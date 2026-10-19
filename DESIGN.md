# YTDL Studio / Obsidian Futuristic

## Implementation

Vanilla HTML, CSS and JavaScript, hosted by the existing Python/pywebview shell.
No frontend framework, remote stylesheet, icon dependency or engine rewrite.
The authenticated browser fallback exposes the same small API as the desktop.

- Canvas #090B10; sidebar #10131B; surface #171B25; elevated #202636.
- Violet #9B8CFF identifies actions, focus and selection. Cyan #69DCEB is reserved
  for active transfers. Text #F2F4FA / #9AA6BB.
- Layout relies on typographic hierarchy, separators, alignment and flat surfaces.
  There is no hero, ambient animation, card stack, glow or glass overlay.
- Sidebar: 232px expanded, 64px collapsed, auto collapse below 1024px.
  Content is capped at 1560px including margins; source rail stacks on small windows.
- Fonts prefer locally installed Inter and Noto Sans Thai, with native fallbacks.
  No bundled font binaries or external font requests.
- Shared transfer rows serve Overview, Downloads and History. Progress polling
  preserves action-button focus. Native window chrome remains unchanged.

## Interactions

The input validates HTTP(S) links locally. Debounced metadata requests are
independent of downloads; stale responses cannot replace a more recent URL.
Metadata errors are non-blocking. Thumbnails, formats and duration come from the
extractor, with explicit unavailable states rather than generated sample data.

Three media modes retain their existing quality ceilings and highest-source
defaults. Advanced access settings stay behind progressive disclosure.
Native paste, text editing and Ctrl/Cmd + Enter remain available. A transfer
dock keeps the current job visible across pages. Search and type filters act on
the real session history. Removing a history record never removes a file.

Appearance and destination preferences persist atomically in a per-user store;
authentication choices remain in memory. Sidebar mode, reduced motion and list
density are implemented. Motion also respects the operating system preference.

## Review and verification (2026-10-19)

- Python suite: 57 tests, including metadata without a download, source modes,
  image processing, cancellation, history removal and preference storage.
- JavaScript syntax, HTML IDs / references, Python compilation and whitespace checks.
- Actual browser navigation through all four pages, quality switching, retained
  per-mode choices, search/filter states, native metadata reads on a local URL,
  appearance settings saved through the real API, and visible 2px keyboard focus.
- Real PNG download from a throttled localhost media server: progress and a
  cross-page dock, completion/history, then cancellation and retry of a second
  transfer. The completed test image was 1200 x 800, approximately 2.9 MB.
- Viewports checked: 2546, 1440, 1024, 800, 640 and 390px. No horizontal page
  overflow was detected in the inspected states. Auto-collapse was checked after
  viewport changes settled. Settings and transfer actions also checked compact.
- No warning/error console messages appeared during the inspected browser workflow.
- Review removed redundant page overlines and numbered decorations, tightened
  vertical spacing, expanded radio hit areas and preserved keyboard action focus.

At the initial redesign stage, screenshot capture timed out; only rendered
geometry and interactions could be checked then. Screenshot capture became
available during the targeted refinement below. The interface uses the native
system font if the preferred fonts are unavailable.

## Existing backend limits retained

One active transfer; no queue, pause or resume. Retry requires the original
request still in the current UI session. History contains eight successful jobs
from the current process, not a persistent library of failures and cancelled jobs.
Folder opening is supported; individual file opening is omitted because final
paths are not uniformly returned. Gallery/image metadata has an explanatory state
instead of a fabricated preview. Installed extractors do not guarantee every URL.

Live social-site transfers and an Apple Silicon build were not verified here.
The macOS packager still includes the entire UI directory and discovers the new
preference module through normal Python imports. No packaged executable was built
on this Windows development run.

## Language support

Settings includes English (`en`), Thai (`th`), Japanese (`ja`) and Simplified
Chinese (`zh-CN`). Language changes apply immediately and persist with ordinary
preferences; older preferences default to Thai. Offline catalogs cover static
copy, live controls, status, help and accessibility labels. Real media titles and
filenames are excluded from static translation capture. Third-party diagnostic
text is preserved after the localized application guidance. Native close-warning
copy follows the saved language; native OS dialog buttons follow the OS locale.

Verified in the actual browser: all four locales, Chinese restored after reload,
Japanese audio quality retained at 320 kbps after switching languages, localized
empty history, and English/Japanese layouts at 780px without horizontal overflow.
The Python suite has 59 tests; `node tests/test_i18n.cjs` additionally checks catalog
coverage, placeholders, translated live values, fallback and raw diagnostics.

## Targeted visual refinement

Kept the application shell, page structure, navigation, localization and download
logic. Changes are limited to styling and a native disclosure around the existing
source directory; no new frontend dependency or application state was introduced.

- Body text is 15px; Thai uses 1.8 line height with normal heading letter spacing.
  Field labels are 14px and helper text 13px, with stronger secondary contrast.
- The existing form has one restrained work surface and a shared section rule.
  Header spacing is tighter; content width is capped at 1680px on large desktops.
- The main action is 50px high with distinct enabled, disabled, hover, pressed and
  keyboard-focus states. Select and format fields align at 44px.
- Sources stay in the existing rail, can be collapsed with a native details
  control, and use two columns on wide desktops. Search, 30 logos, mode-specific
  support and deliberately subdued unsupported sources remain available.
- Active navigation, selected media type and focused inputs use precise strokes;
  there are no new gradients, glow, ambient animation or decorative sections.

Reviewed actual rendered screenshots at 1440 x 1000 and 780 x 860. The primary
action remains fully visible in the inspected compact default state. At 2546px,
both source columns fit without clipped platform names. No horizontal page
overflow was detected in these states. Disclosure, search, media switching,
translated navigation, and enabled/disabled keyboard focus were verified in the
browser with no warning/error logs. The 59 Python tests, Node localization checks,
JavaScript syntax, launcher check and whitespace check passed. Native Apple Silicon
runtime/build validation remains outside this Windows verification.

## Catalog expansion to 50 sources

Added 20 sources with bundled platform marks, domains, and independent media-mode
states. Image-post routing uses the registry, including the 500px and Wikimedia
module aliases. Unsupported modes remain subdued even when gallery-dl is absent.
The icon builder also regenerates the offline preview seed from the same registry.

The Python suite passes 94 tests and the four-language Node checks pass. Actual
browser checks verified all 50 entries, no broken images, source filtering,
audio/video status changes, no console warnings/errors, and a scrollable source
list without horizontal overflow at 780px. The browser screenshot service timed
out; the bundled marks were inspected separately as a contact sheet. No live
download test of all newly listed platforms or native macOS packaging was performed.
