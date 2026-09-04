"""Pricing a custom run against a plan: pytest tests/test_plan_quote.py

The per-location windows feature let one booking run 30 days in a mall and 50 at an
airport. `ensure_plan_locations` caps how many LOCATIONS a plan covers, but nothing capped
or priced the DAYS -- so five locations on a 30-day plan could each be sold a year and
still be billed the 30-day price. This pins the arithmetic that makes that visible.

Pure functions, deliberately: the quote is a calculation over a plan, so it needs no
database and this check runs anywhere. The endpoint that wraps it is covered by the plan
tests that already stand up Postgres.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Importing the app package reads config at import time and dies without these.
os.environ.setdefault("SECRET_KEY", "plan-quote-test-secret-not-for-production")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "mock")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "mock")

from backend.routers.tenant_plans import plan_capacity_screen_days, quote_paise  # noqa: E402


class FakePlan:
    """Just the four columns the quote reads. A real TenantPlan would need a session."""

    def __init__(self, duration_days=30, max_locations=5, price_paise=2_500_000, name="Standard"):
        self.duration_days = duration_days
        self.max_locations = max_locations
        self.price_paise = price_paise
        self.name = name


def test_a_custom_shape_is_priced_in_screen_days():
    # Rs.25,000 / 30 days / 5 locations = 150 screen-days at Rs.166.67 each.
    plan = FakePlan()
    assert plan_capacity_screen_days(plan) == 150

    # The package sold as designed costs the package price, not a penny more.
    assert quote_paise(plan, 150) == 2_500_000

    # Underuse is never a discount. A client taking one location for 30 days is using 30 of
    # 150 screen-days and still pays the full package -- plan_screen_usage already calls the
    # remaining 120 theirs to waste, and the plan_underused alert tells the tenant to fill
    # them. Pro-rating this down would let anyone buy the five-location plan at a fifth.
    assert quote_paise(plan, 30) == 2_500_000
    assert quote_paise(plan, 1) == 2_500_000

    # The real case: 30 days in a mall, 10 in a shop, 50 at an airport = 90 screen-days.
    # Still inside 150, so it is the package price -- a custom SHAPE is not a surcharge.
    assert quote_paise(plan, 30 + 10 + 50) == 2_500_000

    # Past the package, pro-rata. 300 screen-days is twice the capacity, so twice the price.
    assert quote_paise(plan, 300) == 5_000_000
    # And it scales continuously rather than in package-sized jumps: 225 is 1.5x.
    assert quote_paise(plan, 225) == 3_750_000


def test_each_plan_keeps_its_own_rate_per_screen_day():
    # The volume discount in a tenant's own tiers survives, because the rate is read off
    # each plan rather than from one global figure. The same 600 screen-days quoted on the
    # bigger package is half the price -- flattening both onto one rate per screen-day would
    # have thrown that away and undercut the tenant's own price list.
    small = FakePlan(duration_days=30, max_locations=1, price_paise=1_000_000)   # Rs.333/day
    large = FakePlan(duration_days=30, max_locations=10, price_paise=5_000_000)  # Rs.166/day
    assert quote_paise(small, 600) == 20_000_000
    assert quote_paise(large, 600) == 10_000_000

    # Below capacity the floor wins on BOTH, so the cheap plan is the cheap answer only
    # while it fits. 60 screen-days is Rs.20,000 on `small` (twice its package, pro-rata)
    # and Rs.50,000 on `large` (its floor) -- the quote does not pretend the big package is
    # better value for a small run.
    assert quote_paise(small, 60) == 2_000_000
    assert quote_paise(large, 60) == 5_000_000


def test_a_plan_with_nothing_to_divide_by_still_answers():
    # An uncapped plan (max_locations 0 is "no cap" throughout the codebase) has no capacity
    # to divide by. It must return the plan price, not raise ZeroDivisionError on a sale.
    uncapped = FakePlan(max_locations=0)
    assert plan_capacity_screen_days(uncapped) == 0
    assert quote_paise(uncapped, 9_999) == 2_500_000

    # No plan at all: a booking sold on bare dates has nothing to quote against.
    assert plan_capacity_screen_days(None) == 0
    assert quote_paise(None, 100) == 0

    # A free plan stays free however it is shaped -- 0 * anything must not become a price.
    assert quote_paise(FakePlan(price_paise=0), 10_000) == 0


if __name__ == "__main__":
    test_a_custom_shape_is_priced_in_screen_days()
    test_each_plan_keeps_its_own_rate_per_screen_day()
    test_a_plan_with_nothing_to_divide_by_still_answers()
    print("plan quote: all checks passed")
