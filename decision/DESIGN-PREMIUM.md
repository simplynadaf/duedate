# Research: premium enterprise palette + Apple-like depth (2026-10-02)

Goal: make DueDate feel like a billion-dollar enterprise product, with a tasteful
Apple-like 3D/depth feel, WITHOUT turning a legal-aid tool into a gimmicky showreel.

## Color: what "enterprise premium" actually is (verified)
Sources: Vercel Geist color system (read live), Linear/Stripe/Mercury patterns, 2026
UI palette guides.
- A TINTED near-black base, never flat #000. Cool undertone reads most premium.
- TWO background levels: Background 1 (default) and Background 2 (used sparingly for
  subtle differentiation). This two-level depth is the Geist core idea.
- A disciplined neutral scale for borders: default / hover / active (3 steps).
- Off-white text (not #fff): a primary and a muted/secondary, tinted from the base hue.
- ONE confident accent, used sparingly. Navy signals trust for SaaS/finance/legal.
- "Billion-dollar institution" read = deep navy base + champagne GOLD accent (wealth,
  law, trust), or graphite + sapphire (fintech). Gold-on-navy is the most distinctive
  and the best fit for a housing/legal tool.

### LOCKED palette: "Midnight & Champagne" (enterprise, trust, premium)
```
--bg      #080B14   page background 1 (tinted near-black navy)
--bg-2    #0C1120   background 2 (subtle differentiation, sparing)
--surface #10172B   raised component background
--surface2#161F38   hover/active surface
--hair    rgba(226,232,255,.09)    default border
--hair-2  rgba(226,232,255,.16)    hover/active border
--ink     #F4F6FC   primary text (off-white, not pure white)
--ink-soft#A6B0CC   secondary text (tinted from navy)
--ink-faint#6B779A  tertiary
--gold    #D8B972   the one accent (champagne, muted, NOT yellow)
--gold-hi #ECD79B   accent highlight / glow
--gold-ink#2A1F08   text on gold
--sapphire#5B8CFF   a cool secondary ONLY for links/focus if needed (used minimally)
```
Rationale: deep navy + champagne gold is the classic private-bank / enterprise look.
Distinct from the teal we had, and distinct from the common indigo-SaaS default.

## Apple-like depth: the techniques, ranked for THIS tool
Sources: Apple AirPods canvas technique (setproduct, mejba.me, builder.io), Codrops GSAP
cinematic scroll, finesse-ui "subtle beats showy", Chrome performant-parallax.

1. How Apple ACTUALLY does product scroll: a <canvas> fed a PRE-RENDERED image frame
   sequence; GSAP ScrollTrigger maps scroll -> frame index ("locked to your finger").
   VERDICT: overkill here. It needs rendered 3D frames and suits a product beauty-shot,
   not a form-based legal tool. Skip for the app; it is a technique to remember for a
   future product-style landing page.

2. Pointer-tilt 3D on the hero / key card: CSS `perspective` + `rotate3d` driven by
   pointer position, transform-only. Gives real Apple-like parallax depth, cheap, 60fps.
   VERDICT: ADOPT, subtly, on the deadline hero (the one hero moment).

3. Layered parallax depth: foreground and background planes move at different speeds on
   scroll/pointer (transform-only). VERDICT: ADOPT lightly as background glow drift +
   a slight hero lift on scroll. Keep gentle.

4. Specular / light-sweep sheen on the primary surface and the gold accent (moving
   highlight), @property-animated. VERDICT: ADOPT on the deadline card edge only.

### Hard rules (every source agrees)
- Animate ONLY transform and opacity in anything scroll/pointer-driven. Never width/
  height/top/left/box-shadow on each tick (layout thrash = stutter).
- Custom easing, not linear/ease-in-out. Exponential ease-out.
- Respect prefers-reduced-motion: disable tilt + parallax, keep static.
- Subtle beats showy. This is a tool a frightened person uses; depth should feel
  expensive and calm, never distracting. No cursor hijack, no mandatory scroll scrub.

## Plan
Reskin to Midnight & Champagne, add: (a) pointer-tilt on the deadline hero, (b) gentle
background parallax drift, (c) a slow specular sheen on the gold accent edge, (d) keep
the IntersectionObserver reveals and themed browser surfaces already in place. Re-render
desktop + mobile + OG, redeploy, verify reduced-motion. Keep zero em dashes.
