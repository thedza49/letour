---
name: Vitesse de France
colors:
  surface: '#131315'
  surface-dim: '#131315'
  surface-bright: '#39393b'
  surface-container-lowest: '#0e0e10'
  surface-container-low: '#1b1b1d'
  surface-container: '#201f21'
  surface-container-high: '#2a2a2c'
  surface-container-highest: '#353437'
  on-surface: '#e5e1e4'
  on-surface-variant: '#cec6ab'
  inverse-surface: '#e5e1e4'
  inverse-on-surface: '#303032'
  outline: '#979177'
  outline-variant: '#4c4732'
  surface-tint: '#e2c600'
  primary: '#fffcff'
  on-primary: '#383000'
  primary-container: '#ffe000'
  on-primary-container: '#716300'
  inverse-primary: '#6c5e00'
  secondary: '#75dc8b'
  on-secondary: '#003916'
  secondary-container: '#007e39'
  on-secondary-container: '#c2ffc8'
  tertiary: '#fffcff'
  on-tertiary: '#68001a'
  tertiary-container: '#ffd7d8'
  on-tertiary-container: '#c7003a'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffe33b'
  primary-fixed-dim: '#e2c600'
  on-primary-fixed: '#211b00'
  on-primary-fixed-variant: '#524700'
  secondary-fixed: '#91f9a4'
  secondary-fixed-dim: '#75dc8b'
  on-secondary-fixed: '#00210a'
  on-secondary-fixed-variant: '#005323'
  tertiary-fixed: '#ffdada'
  tertiary-fixed-dim: '#ffb3b6'
  on-tertiary-fixed: '#40000c'
  on-tertiary-fixed-variant: '#920028'
  background: '#131315'
  on-background: '#e5e1e4'
  surface-variant: '#353437'
typography:
  display-lg:
    fontFamily: Barlow Condensed
    fontSize: 48px
    fontWeight: '800'
    lineHeight: 52px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Barlow Condensed
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 30px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Barlow Condensed
    fontSize: 20px
    fontWeight: '700'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-caps:
    fontFamily: Barlow Condensed
    fontSize: 13px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.08em
  stat-lg:
    fontFamily: JetBrains Mono
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  stat-sm:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  display-lg-mobile:
    fontFamily: Barlow Condensed
    fontSize: 36px
    fontWeight: '800'
    lineHeight: 40px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 16px
  margin-mobile: 16px
  margin-desktop: 32px
---

## Brand & Style

The design system is built on a foundation of **Modern French Racing**, a style that marries the gritty, high-performance atmosphere of professional cycling with a clean, contemporary digital aesthetic. The system prioritizes speed, precision, and heritage, evoking the sensation of the peloton moving through the French countryside.

The visual direction utilizes a **High-Contrast / Bold** approach. It leans heavily on massive, condensed typography and a dark, asphalt-inspired base to allow the iconic race colors to vibrate with intensity. To ground the digital experience in the physical race, the design incorporates topographic patterns inspired by Alpine climb profiles and subtle French tricolor accents (blue, white, and red ribbons) to maintain a sense of place and prestige. 

The emotional response should be one of urgency and professionalism—mirroring the split-second decision-making required by a team director during a mountain stage.

## Colors

The palette is derived directly from the iconography of the Tour. The **Primary (Tour Yellow)** is the focal point, reserved for the most critical actions and the "Maillot Jaune" status. The **Neutral (Deep Asphalt)** serves as the road—a dark, textured canvas that reduces glare and provides high legibility for dense data.

- **Primary (Yellow):** Used for active states, primary buttons, and seasonal point totals.
- **Secondary (Points Green):** Used for success states, "In-Race" status, and value increases.
- **Tertiary (Polka-Dot Red):** Reserved for "Out of Race" (DNF/DNS) status, errors, and removal actions.
- **Neutral (Asphalt/White):** A scale of deep greys (`#121214` to `#2D2D32`) for surfaces, with crisp white for maximum text contrast.
- **Tricolor Accents:** Use French Blue (`#002395`) and French Red (`#ED2939`) only as thin decorative ribbons or "heritage" badges.

## Typography

This system uses a dual-font strategy to balance athletic energy with data density. 

**Barlow Condensed** is the voice of the race. It is used for all headings and navigational elements. Its tall, narrow profile allows for high-impact messaging even on narrow mobile screens. It should almost always be set in uppercase to mimic race-side stencils and signage.

**Inter** provides a neutral, highly readable foundation for player names, descriptions, and UI instructions.

**JetBrains Mono** is utilized for all numerical data. This ensures that rider prices, points, and times align perfectly in vertical columns, allowing users to scan and compare stats with mechanical precision.

## Layout & Spacing

The layout philosophy follows a **Fluid Grid** model with a mobile-first priority. Given the density of rider statistics, the layout is designed to be "compact but breathable," utilizing a 4px baseline rhythm.

- **Mobile (Default):** 1-column stack with 16px side margins. Data tables may use horizontal scrolling or condensed views to keep the 9-rider roster visible on a single viewport height.
- **Desktop (768px+):** Transitions to a 12-column grid. The "Roster Creator" typically uses a 2/3 (Market) and 1/3 (Your Team) split or a 2-column dashboard.
- **Gutter Strategy:** 16px gutters are standard to maintain clear separation between dense data modules.
- **Density:** Padding within list items is kept to a minimum (8-12px vertical) to ensure the maximum number of riders can be seen at once without excessive scrolling.

## Elevation & Depth

Hierarchy is established through **Tonal Layers** rather than heavy shadows, maintaining a sleek, modern feel.

- **Base Layer:** The darkest grey (`#121214`) represents the "road."
- **Surface Layer:** Cards and containers use a slightly lighter grey (`#1E1E22`) to sit above the base.
- **Interactive Layer:** Inputs and active items use a third level of grey (`#2D2D32`).
- **Outlines:** Instead of shadows, use 1px "Zinc" outlines (`#3F3F46`) to define boundaries. 
- **Accent Elevation:** The primary "Yellow" components use no elevation—their color contrast provides all the necessary depth.
- **Topographic Dividers:** Use low-opacity lines that mimic mountain elevation profiles as section separators to add a "Tactile" heritage feel without cluttering the UI.

## Shapes

The shape language is **Soft (0.25rem)**. This slight rounding provides a professional, "engineered" feel that avoids the playfulness of fully rounded systems or the harshness of zero-radius brutalism. 

- **Standard Elements:** Buttons and cards use a 4px (`0.25rem`) radius.
- **Status Pills:** Jersey status indicators (Yellow, Green, Red) use `rounded-xl` or full pill shapes to distinguish them from structural UI components.
- **Media:** Rider headshots should use the standard 4px radius for a clean, card-based look.

## Components

### Buttons
- **Primary:** Solid Tour Yellow background, Black Barlow Condensed Bold text. 4px radius. 
- **Secondary:** Outlined Zinc, White text. Turns Yellow on hover.
- **Captain Toggle:** A specialized button that, when active, turns Yellow with a star icon.

### Cards
- **Rider Card:** Features the "Asphalt" background, a 1px border, and a 3px French Tricolor ribbon at the top edge. 
- **Stats Panel:** Uses Mono fonts for numbers. Compact vertical padding.

### Lists (The Peloton Table)
- High-density rows with alternating "Asphalt" shades for zebra-striping. 
- Right-aligned Mono stats for quick comparison.
- "OUT" riders are displayed at 50% opacity with a Polka-Dot Red badge.

### Inputs
- Dark backgrounds with 1px white or yellow borders on focus.
- No shadows; focus is indicated by a crisp color change of the border.

### Jerseys & Badges
- Small, circular or jersey-shaped badges indicate the current leaders in various categories (Yellow, Green, Polka-Dot, White). These are the only elements allowed to break the standard color palette.