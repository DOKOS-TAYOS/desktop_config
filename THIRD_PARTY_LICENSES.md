# Third-Party Licenses

This repository is licensed under the MIT License. This file summarizes the production third-party Python packages reviewed for the Streamlit Community Cloud deployment.

Scope notes:

- The inventory below tracks the production dependency set pinned in `requirements.txt` plus its resolved transitive dependencies.
- Development-only tooling lives in `requirements-dev.txt` and is intentionally outside this production deployment inventory.
- This is a review summary, not a replacement for each package's original license text.
- Where available, the original license files are bundled inside each package's `.dist-info` directory in `.venv/Lib/site-packages/`.

## License verdict

- Direct project license: MIT
- Direct dependencies: all direct dependencies use permissive licenses
- Installed dependency set: not all installed dependencies are permissive
- Notable exception: `certifi` is licensed under `MPL-2.0`, which is generally treated as weak copyleft rather than permissive
- `requests` is no longer a direct project dependency, but it is still installed transitively through `streamlit`
- No GPL, AGPL, or LGPL packages were detected in the installed environment reviewed here

## Package inventory

| Package | Version | Direct dependency | Reported license | Verdict |
| --- | --- | --- | --- | --- |
| altair | 6.1.0 | no | BSD-style license text | Permissive |
| attrs | 26.1.0 | no | MIT | Permissive |
| blinker | 1.9.0 | no | MIT License | Permissive |
| cachetools | 7.0.6 | no | MIT | Permissive |
| certifi | 2026.4.22 | no | MPL-2.0 | Weak copyleft |
| charset-normalizer | 3.4.7 | no | MIT | Permissive |
| click | 8.3.3 | no | BSD-3-Clause | Permissive |
| colorama | 0.4.6 | no | BSD License | Permissive |
| gitdb | 4.0.12 | no | BSD License | Permissive |
| GitPython | 3.1.49 | no | BSD-3-Clause | Permissive |
| h5py | 3.16.0 | no | BSD-3-Clause | Permissive |
| idna | 3.13 | no | BSD-3-Clause | Permissive |
| Jinja2 | 3.1.6 | no | BSD License | Permissive |
| jsonschema | 4.26.0 | no | MIT | Permissive |
| jsonschema-specifications | 2025.9.1 | no | MIT | Permissive |
| MarkupSafe | 3.0.3 | no | BSD-3-Clause | Permissive |
| narwhals | 2.20.0 | no | MIT License | Permissive |
| numpy | 2.4.3 | yes | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | Permissive |
| packaging | 26.2 | no | Apache-2.0 OR BSD-2-Clause | Permissive |
| pandas | 2.3.3 | yes | BSD-3-Clause | Permissive |
| pillow | 12.2.0 | no | MIT-CMU | Permissive |
| pip | 25.0.1 | no | MIT | Permissive |
| plotly | 6.6.0 | yes | MIT License | Permissive |
| protobuf | 6.33.6 | no | BSD-3-Clause | Permissive |
| pvlib | 0.15.0 | yes | BSD-3-Clause | Permissive |
| pyarrow | 24.0.0 | no | Apache-2.0 | Permissive |
| pydeck | 0.9.2 | no | Apache-2.0 | Permissive |
| Pygments | 2.20.0 | no | BSD-2-Clause | Permissive |
| python-dateutil | 2.9.0.post0 | no | BSD / Apache dual license | Permissive |
| pytz | 2026.1.post1 | no | MIT | Permissive |
| referencing | 0.37.0 | no | MIT | Permissive |
| requests | 2.32.5 | no | Apache-2.0 | Permissive |
| rpds-py | 0.30.0 | no | MIT | Permissive |
| scipy | 1.17.1 | no | BSD License classifier | Permissive |
| six | 1.17.0 | no | MIT | Permissive |
| smmap | 5.0.3 | no | BSD-3-Clause | Permissive |
| streamlit | 1.55.0 | yes | Apache-2.0 | Permissive |
| tenacity | 9.1.4 | no | Apache-2.0 | Permissive |
| toml | 0.10.2 | no | MIT | Permissive |
| tornado | 6.5.5 | no | Apache-2.0 | Permissive |
| typing_extensions | 4.15.0 | no | PSF-2.0 | Permissive |
| tzdata | 2026.2 | no | Apache-2.0 | Permissive |
| urllib3 | 2.6.3 | no | MIT | Permissive |
| watchdog | 6.0.0 | no | Apache-2.0 | Permissive |

## Practical publication note

Using MIT for your own repository is compatible with this dependency set, but it would not be accurate to say that every installed dependency is permissive because `certifi` is `MPL-2.0`. Removing `requests` from `requirements.txt` reduces direct dependencies but does not remove `certifi` from the installed environment while `streamlit` continues to depend on `requests`.
