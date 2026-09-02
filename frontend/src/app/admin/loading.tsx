/**
 * Shown while an admin route loads.
 *
 * /dashboard has had one of these since the start; /admin never did, so moving between
 * admin pages left the previous screen sitting there with no sign anything was happening.
 * Styled for the dark admin shell rather than reusing the dashboard skeleton, which is
 * light and would flash white inside this layout.
 */
export default function AdminLoading() {
  return (
    <div className="space-y-6 p-5 lg:p-8" aria-busy="true" aria-label="Loading">
      <div className="space-y-3">
        <div className="h-3 w-24 animate-pulse rounded bg-white/5" />
        <div className="h-8 w-72 max-w-full animate-pulse rounded bg-white/5" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="h-28 animate-pulse rounded-2xl bg-white/5" />
        ))}
      </div>
      <div className="h-96 animate-pulse rounded-2xl bg-white/5" />
    </div>
  )
}
