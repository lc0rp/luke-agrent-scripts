# Install Recipes

Use these on the fly when the project needs a stronger web UI foundation.

Verify the package manager and framework before running installs.

## Base UI Stack

For React / Next.js style projects, a strong default is:
- `shadcn/ui`
- `Radix UI`
- `lucide-react`
- `class-variance-authority`
- `tailwind-merge`
- `clsx`

React plus Tailwind remains a strong default for GPT-5.4-era web work because it is fast to iterate and easy to theme consistently.

Typical install flow:

```bash
npx shadcn@latest init
pnpm add class-variance-authority clsx tailwind-merge lucide-react
```

Add components as needed:

```bash
pnpm dlx shadcn@latest add button input textarea card dialog dropdown-menu table tabs badge toast
```

## Motion

If the UI needs meaningful motion:

```bash
pnpm add motion
```

Use sparingly. One or two high-value motion moments beat many effects.

## Visual QA

For screenshot-driven review:

```bash
pnpm add -D @playwright/test
npx playwright install
```

Then use browser screenshots and critique passes instead of text-only iteration.

When visual accuracy matters, verify multiple breakpoints and check that fixed or floating elements do not overlap key content.

## AI-Native UI Patterns

If the product includes chat or assistant surfaces, inspect:

- [Vercel AI Elements](https://github.com/vercel/ai-elements)
- [Prompt Kit](https://github.com/ibelick/prompt-kit)

Borrow patterns selectively. Do not clone their entire visual language into unrelated products.

## Fonts

Prefer project-native fonts first.

If none exist, choose one deliberate display/body pairing that fits the product. Avoid defaulting to generic system-safe combinations solely because they are easy.

## When Not To Install More

Do not add a UI stack just to restyle a small screen if the existing project already has:

- stable tokens
- reusable components
- acceptable primitives

In that case, extend the current system instead of replacing it.
