# License decision — GPL-3.0-only

On 2026-11-01 the project owner explicitly selected **GNU General Public License
version 3 only** for original NÜVEL Studio code the owner has authority to license.
The decision is implemented in [LICENSE](../LICENSE), [COPYRIGHT](../COPYRIGHT)
and practical per-file SPDX headers. Public attribution is
**Copyright © 2026 Lumin0usX**. This grants permissions, not copyright ownership.

The earlier recommendation is now an adopted decision for the scoped original
work. It is not an assurance that every repository asset or bundled executable
is cleared. Choosing the main project license does not waive any third-party
source, attribution or license-compatibility obligations.

## Scope and contributions

- Use SPDX **GPL-3.0-only**, not GPL-3.0-or-later. The unmodified GPLv3 license
  appendix's generic “or later” example is not the project's version selection.
- Preserve legitimate owner, contributor and third-party notices. Contributors
  retain copyright and submit applicable original work under project terms;
  there is no CLA or copyright assignment. See [CONTRIBUTING.md](../CONTRIBUTING.md).
- Fonts, dependencies, SDKs, runtimes and other third-party code keep their own
  licenses. The owner cannot relicense rights held by others.
- Name/logo/brand rights are separate. Artwork is excluded from the new code
  grant; no asset license or registered status is invented. See
  [BRAND-NOTICE.md](../BRAND-NOTICE.md).
- The SVG sprite in `ui/index.html` uses Feather 4.29.2 under MIT, with retained
  Cole Bemis attribution and [source evidence](../third_party/feather/PROVENANCE.md).
  No file-wide GPL header is applied to that mixed HTML file. The owner confirms
  the separate brand kit's ChatGPT Image Generation origin; artwork terms remain
  unchanged and no exclusive rights or third-party clearance are asserted.

## Why the decision fits the original-code grant

Retaining mutagen preserves functionality. Its verified 1.48.1 header and
metadata say **GPL-2.0-or-later**, permitting a GPLv3 compliance path for a covered
combination; it is not relicensed as GPL-3.0-only. Original-code licensing and
obligations for a distributed combination remain different questions.
[Pinned mutagen header](https://raw.githubusercontent.com/quodlibet/mutagen/release-1.48.1/mutagen/__init__.py).

Selecting GPL-3.0-only for original work avoids a speculative dependency
replacement and makes incoming project terms explicit. It allows legitimate
use, study, modification and redistribution, including commercial use, subject
to GPL conditions. It does not require transferring copyright to the maintainer
or add an always-visible GUI credit condition. Applicable GPL notice duties
still apply. No license guarantees immunity from legal claims.

## Third-party release blockers remain active

| Component | Decision and remaining obligations |
| --- | --- |
| mutagen 1.48.1 | Keep GPL-2.0-or-later notices and matching applicable source/build materials. The main license does not provide those materials automatically. |
| gallery-dl / requests | Existing frozen CLI combines GPLv2-only gallery with Apache-2.0 requests. No applicable permission/compatible release has been verified. Current build/collect/publish hold remains. GUI subprocess separation does not resolve the internal CLI. |
| Generated gallery entry | If copyrightable and covered by the original-code grant, GPL-3.0-only does not permit combining it with GPLv2-only code. No GPLv2-compatible per-file grant/exception is adopted here. Keep this independent review/blocker. |
| FFmpeg | Existing Mac files are GPL builds; required LGPL replacements and exact source/library/build provenance remain absent. Main-project GPL adoption does not waive the LGPL packaging policy or corresponding-source duties. |
| yt-dlp / native / frozen components | Preserve actual package/vendor, Python/runtime, PyInstaller exception/runtime-hook, SDK and native-library grants/notices and applicable sources. No wrapper license is applied to every embedded component. |
| Assets and history | Kit AI origin is owner-confirmed; existing asset terms unchanged. Local Strategy B replaced the inventoried artwork and sprites with MIT Feather adaptations; remote copies remain unverified. Email/path disclosure is accepted. Fonts keep OFL texts/hashes. |

**Public source publication requires a separate owner decision.** The license
selection is resolved for scoped original code; local history remediation is
complete. This license commit does not establish source ownership for unidentified
third-party material or removal of old artwork from remote copies. Existing
identity/path disclosure is accepted. Windows builds or notarization are not
prerequisites for publishing only source.

**Public Windows Binary: BLOCKED. Public macOS Binary: BLOCKED.** Exact third-party
compatibility, source/notice/native closure, security and native acceptance are
still outstanding. See [third-party notices](../THIRD_PARTY_NOTICES.md).
No dependency, compliance gate, application behavior, installed app or remote
state was changed by adopting the original-code license.
