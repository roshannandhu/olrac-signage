// Architecture fitness functions for the frontend. Run: `npx depcruise src`.
// Locks the layering the code already follows so it cannot drift: pages (src/app) may use
// components and lib; components may use lib; lib is the shared floor (types, api, utils)
// and imports neither. Dependencies point down, never up — and never in a circle.
/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: 'no-circular',
      severity: 'error',
      comment: 'Circular imports make modules impossible to reason about, test, or reuse.',
      from: {},
      to: { circular: true },
    },
    {
      name: 'lib-is-the-floor',
      severity: 'error',
      comment:
        'src/lib is shared utilities/types/api — the bottom layer. It must not import UI ' +
        '(src/app pages or src/components). If it needs to, the thing it needs belongs in lib.',
      from: { path: '^src/lib' },
      to: { path: '^src/(app|components)' },
    },
    {
      name: 'components-not-into-pages',
      severity: 'error',
      comment:
        'Reusable components must not import page code (src/app). A component that needs a ' +
        "page's data should receive it as props; data flows down, not up.",
      from: { path: '^src/components' },
      to: { path: '^src/app' },
    },
  ],
  options: {
    doNotFollow: { path: 'node_modules' },
    exclude: { path: 'node_modules' },
    tsConfig: { fileName: 'tsconfig.json' },
    tsPreCompilationDeps: true,
  },
};
