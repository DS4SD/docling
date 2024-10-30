## [v2.3.1](https://github.com/DS4SD/docling/releases/tag/v2.3.1) - 2024-10-30

### Fix

* Simplify torch dependencies and update pinned docling deps ([#190](https://github.com/DS4SD/docling/issues/190)) ([`eb679cc`](https://github.com/DS4SD/docling/commit/eb679ccbb484fc3ef50dcf00be54ccd488d4a34d))
* Allow to explicitly initialize the pipeline ([#189](https://github.com/DS4SD/docling/issues/189)) ([`904d24d`](https://github.com/DS4SD/docling/commit/904d24d6005d113c50bde0ad398fdaafbbfb3027))

## [v2.3.0](https://github.com/DS4SD/docling/releases/tag/v2.3.0) - 2024-10-30

### Feature

* Add pipeline timings and toggle visualization, establish debug settings ([#183](https://github.com/DS4SD/docling/issues/183)) ([`2a2c65b`](https://github.com/DS4SD/docling/commit/2a2c65bf4f89a715c27310eaa9cd9db635e0f673))

### Fix

* Fix duplicate title and heading + add e2e tests for html and docx ([#186](https://github.com/DS4SD/docling/issues/186)) ([`f542460`](https://github.com/DS4SD/docling/commit/f542460af3c7676e5f8dee3b6ce729b139560cd6))

## [v2.2.1](https://github.com/DS4SD/docling/releases/tag/v2.2.1) - 2024-10-28

### Fix

* Fix header levels for DOCX & HTML ([#184](https://github.com/DS4SD/docling/issues/184)) ([`b9f5c74`](https://github.com/DS4SD/docling/commit/b9f5c74a7d13827c2b7887ddbf0b4eb43edd0846))
* Handling of long sequence of unescaped underscore chars in markdown ([#173](https://github.com/DS4SD/docling/issues/173)) ([`94d0729`](https://github.com/DS4SD/docling/commit/94d0729c500b0be8ac4a1cd3025b42048f6e8d5a))
* HTML backend, fixes for Lists and nested texts ([#180](https://github.com/DS4SD/docling/issues/180)) ([`7d19418`](https://github.com/DS4SD/docling/commit/7d19418b779408c345473af684de6b7f60872b6e))
* MD Backend, fixes to properly handle trailing inline text and emphasis in headers ([#178](https://github.com/DS4SD/docling/issues/178)) ([`88c1673`](https://github.com/DS4SD/docling/commit/88c16730571afdd3bfb8894f64d41b5e99bc5a5b))

### Documentation

* Update LlamaIndex docs for Docling v2 ([#182](https://github.com/DS4SD/docling/issues/182)) ([`2cece27`](https://github.com/DS4SD/docling/commit/2cece27208c4bce715d20000b845794dfb97843d))
* Fix batch convert ([#177](https://github.com/DS4SD/docling/issues/177)) ([`189d3c2`](https://github.com/DS4SD/docling/commit/189d3c2d44ec389856f48696eaa78ac9f02f8cde))
* Add export with embedded images ([#175](https://github.com/DS4SD/docling/issues/175)) ([`8d356aa`](https://github.com/DS4SD/docling/commit/8d356aa24715433d458eff4f5f0937ff5cb9cc69))

## [v2.2.0](https://github.com/DS4SD/docling/releases/tag/v2.2.0) - 2024-10-23

### Feature

* Update to docling-parse v2 without history ([#170](https://github.com/DS4SD/docling/issues/170)) ([`4116819`](https://github.com/DS4SD/docling/commit/4116819b515a0611e8e5bf2bb0e1e39f1096b7bf))
* Support AsciiDoc and Markdown input format ([#168](https://github.com/DS4SD/docling/issues/168)) ([`3023f18`](https://github.com/DS4SD/docling/commit/3023f18ba0462a224f75ea40953b5605abef6427))

### Fix

* Set valid=false for invalid backends ([#171](https://github.com/DS4SD/docling/issues/171)) ([`3496b48`](https://github.com/DS4SD/docling/commit/3496b4838fd52cb0d74eadf78b27c19f633871b1))

## [v2.1.0](https://github.com/DS4SD/docling/releases/tag/v2.1.0) - 2024-10-18

### Feature

* Add coverage_threshold to skip OCR for small images ([#161](https://github.com/DS4SD/docling/issues/161)) ([`b346faf`](https://github.com/DS4SD/docling/commit/b346faf622190c4895dffdc1ee2365b3f7808cbc))

### Fix

* Fix legacy doc ref ([#162](https://github.com/DS4SD/docling/issues/162)) ([`63bef59`](https://github.com/DS4SD/docling/commit/63bef59d9ed6cfd937aefd36a4ef38a54a10dac5))

### Documentation

* Typo fix ([#155](https://github.com/DS4SD/docling/issues/155)) ([`f799e77`](https://github.com/DS4SD/docling/commit/f799e777c1248559eb2f84bc334e392cd3c98e49))
* Add graphical band in readme ([#154](https://github.com/DS4SD/docling/issues/154)) ([`034a411`](https://github.com/DS4SD/docling/commit/034a4110573df3ac88fd623970958f02309dd6da))
* Add use docling ([#150](https://github.com/DS4SD/docling/issues/150)) ([`61c092f`](https://github.com/DS4SD/docling/commit/61c092f445ccde8ed5d7c0f2fa91a3d19a1f7a1e))

## [v2.0.0](https://github.com/DS4SD/docling/releases/tag/v2.0.0) - 2024-10-16

### Feature

* Docling v2 ([#117](https://github.com/DS4SD/docling/issues/117)) ([`7d3be0e`](https://github.com/DS4SD/docling/commit/7d3be0edebb420f5840499aa04e4ab928d33cda2))

### Breaking

* Docling v2 ([#117](https://github.com/DS4SD/docling/issues/117)) ([`7d3be0e`](https://github.com/DS4SD/docling/commit/7d3be0edebb420f5840499aa04e4ab928d33cda2))

### Documentation

* Introduce docs site ([#141](https://github.com/DS4SD/docling/issues/141)) ([`d504432`](https://github.com/DS4SD/docling/commit/d504432c1ee250ea417e8239ff5c16c5bec5a2c7))

## [v1.20.0](https://github.com/DS4SD/docling/releases/tag/v1.20.0) - 2024-10-11

### Feature

* New experimental docling-parse v2 backend ([#131](https://github.com/DS4SD/docling/issues/131)) ([`5e4944f`](https://github.com/DS4SD/docling/commit/5e4944f15f0ac1faf3e6a532c3e3ab4da56517a3))

## [v1.19.1](https://github.com/DS4SD/docling/releases/tag/v1.19.1) - 2024-10-11

### Fix

* Remove stderr from tesseract cli and introduce fuzziness in the text validation of OCR tests ([#138](https://github.com/DS4SD/docling/issues/138)) ([`dae2a3b`](https://github.com/DS4SD/docling/commit/dae2a3b66732e1e135b00cce24226c7d9f2eb2e4))

### Documentation

* Simplify LlamaIndex example using Docling extension ([#135](https://github.com/DS4SD/docling/issues/135)) ([`5f1bd9e`](https://github.com/DS4SD/docling/commit/5f1bd9e9c8a19c667d1d587a557c3c36df494762))

## [v1.19.0](https://github.com/DS4SD/docling/releases/tag/v1.19.0) - 2024-10-08

### Feature

* Add options for choosing OCR engines ([#118](https://github.com/DS4SD/docling/issues/118)) ([`f96ea86`](https://github.com/DS4SD/docling/commit/f96ea86a00fd1aafaa57025e46b5288b43958725))

## [v1.18.0](https://github.com/DS4SD/docling/releases/tag/v1.18.0) - 2024-10-03

### Feature

* New torch-based docling models ([#120](https://github.com/DS4SD/docling/issues/120)) ([`2422f70`](https://github.com/DS4SD/docling/commit/2422f706a1b02a679bcbaaba097fef2f69aba0f4))

## [v1.17.0](https://github.com/DS4SD/docling/releases/tag/v1.17.0) - 2024-10-03

### Feature

* Windows support ([#122](https://github.com/DS4SD/docling/issues/122)) ([`d44c62d`](https://github.com/DS4SD/docling/commit/d44c62d7ce6990bbc78bf53315dd76d35d1f6c2e))

## [v1.16.1](https://github.com/DS4SD/docling/releases/tag/v1.16.1) - 2024-09-27

### Fix

* Allow usage of opencv 4.6.x ([#110](https://github.com/DS4SD/docling/issues/110)) ([`34bd887`](https://github.com/DS4SD/docling/commit/34bd887a7f9c11b2b051bdb4707dfdc5f43e6ad5))

### Documentation

* Document chunking ([#111](https://github.com/DS4SD/docling/issues/111)) ([`c05b692`](https://github.com/DS4SD/docling/commit/c05b692d69b6dae1ac5f518e84b17f32e7d94372))

## [v1.16.0](https://github.com/DS4SD/docling/releases/tag/v1.16.0) - 2024-09-27

### Feature

* Support tableformer model choice ([#90](https://github.com/DS4SD/docling/issues/90)) ([`d6df76f`](https://github.com/DS4SD/docling/commit/d6df76f90b249bf48a509b63fa18f570be39482e))

## [v1.15.0](https://github.com/DS4SD/docling/releases/tag/v1.15.0) - 2024-09-24

### Feature

* Add figure in markdown ([#98](https://github.com/DS4SD/docling/issues/98)) ([`6a03c20`](https://github.com/DS4SD/docling/commit/6a03c208ecc9176b0be413594114ce8a3f213371))

## [v1.14.0](https://github.com/DS4SD/docling/releases/tag/v1.14.0) - 2024-09-24

### Feature

* Add URL support to CLI ([#99](https://github.com/DS4SD/docling/issues/99)) ([`3c46e42`](https://github.com/DS4SD/docling/commit/3c46e4266cf1ad8d3a99aa33636d84d34222b4fe))

### Fix

* Fix OCR setting for pypdfium, minor refactor ([#102](https://github.com/DS4SD/docling/issues/102)) ([`d96b96c`](https://github.com/DS4SD/docling/commit/d96b96c8481a8ae68545a34aaf9b8d5a6637a6be))

### Documentation

* Document CLI, minor README revamp ([#100](https://github.com/DS4SD/docling/issues/100)) ([`f8f2303`](https://github.com/DS4SD/docling/commit/f8f2303348c4bbcb7903ff172746a69607e53271))

## [v1.13.1](https://github.com/DS4SD/docling/releases/tag/v1.13.1) - 2024-09-23

### Fix

* Updated the render_as_doctags with the new arguments from docling-core ([#93](https://github.com/DS4SD/docling/issues/93)) ([`4794ce4`](https://github.com/DS4SD/docling/commit/4794ce460a542a730fd5a72a7be7f94a07ed5d12))

## [v1.13.0](https://github.com/DS4SD/docling/releases/tag/v1.13.0) - 2024-09-18

### Feature

* Add table exports ([#86](https://github.com/DS4SD/docling/issues/86)) ([`f19bd43`](https://github.com/DS4SD/docling/commit/f19bd437984f77067d33d591e25c5d5c92d7e0a9))

### Fix

* Bumped the glm version and adjusted the tests ([#83](https://github.com/DS4SD/docling/issues/83)) ([`442443a`](https://github.com/DS4SD/docling/commit/442443a102d91b19a7eb38b316dada89c86ea8a8))

### Documentation

* Updated Docling logo.png with transparent background ([#88](https://github.com/DS4SD/docling/issues/88)) ([`0da7519`](https://github.com/DS4SD/docling/commit/0da75198967c9cffd42be3f3acd6ade2341fc1f5))

## [v1.12.2](https://github.com/DS4SD/docling/releases/tag/v1.12.2) - 2024-09-17

### Fix

* **tests:** Adjust the test data to match the new version of LayoutPredictor ([#82](https://github.com/DS4SD/docling/issues/82)) ([`fa9699f`](https://github.com/DS4SD/docling/commit/fa9699fa3cd2d367382d7b952d0365983a870848))

## [v1.12.1](https://github.com/DS4SD/docling/releases/tag/v1.12.1) - 2024-09-16

### Fix

* CLI compatibility with python 3.10 and 3.11 ([#79](https://github.com/DS4SD/docling/issues/79)) ([`2870fdc`](https://github.com/DS4SD/docling/commit/2870fdc857d02efeb8f1de7852e9577dd3eb2f51))

## [v1.12.0](https://github.com/DS4SD/docling/releases/tag/v1.12.0) - 2024-09-13

### Feature

* Add docling cli ([#75](https://github.com/DS4SD/docling/issues/75)) ([`9899078`](https://github.com/DS4SD/docling/commit/98990784dfa6009b72ee2e1508948b22b00245ec))

### Documentation

* Showcase RAG with LlamaIndex and LangChain ([#71](https://github.com/DS4SD/docling/issues/71)) ([`53569a1`](https://github.com/DS4SD/docling/commit/53569a10238a821dfbbfcef9d2376d179e62a1db))

## [v1.11.0](https://github.com/DS4SD/docling/releases/tag/v1.11.0) - 2024-09-10

### Feature

* Adding txt and doctags output ([#68](https://github.com/DS4SD/docling/issues/68)) ([`bdfdfbf`](https://github.com/DS4SD/docling/commit/bdfdfbf092fdaca43ddef28f763ef04456b82890))

## [v1.10.0](https://github.com/DS4SD/docling/releases/tag/v1.10.0) - 2024-09-10

### Feature

* Linux arm64 support and reducing dependencies ([#69](https://github.com/DS4SD/docling/issues/69)) ([`27a7a15`](https://github.com/DS4SD/docling/commit/27a7a152e1123df7a22c44bb1adab5acce8f5390))

## [v1.9.0](https://github.com/DS4SD/docling/releases/tag/v1.9.0) - 2024-09-03

### Feature

* Export document pages as multimodal output ([#54](https://github.com/DS4SD/docling/issues/54)) ([`1de2e4f`](https://github.com/DS4SD/docling/commit/1de2e4f924f562139c2a1e6314364845f9256575))

### Documentation

* Update MAINTAINERS.md ([#59](https://github.com/DS4SD/docling/issues/59)) ([`69e5d95`](https://github.com/DS4SD/docling/commit/69e5d951a389a9d36134629cfa2a0496c3bf095a))
* Mention quackling on README ([#58](https://github.com/DS4SD/docling/issues/58)) ([`85b7348`](https://github.com/DS4SD/docling/commit/85b7348846c87b28981f23c4855e49857c5bb782))

## [v1.8.5](https://github.com/DS4SD/docling/releases/tag/v1.8.5) - 2024-08-30

### Fix

* Add unit tests ([#51](https://github.com/DS4SD/docling/issues/51)) ([`48f4d1b`](https://github.com/DS4SD/docling/commit/48f4d1ba5288b54d96740a1132b0d7977bef01cf))

## [v1.8.4](https://github.com/DS4SD/docling/releases/tag/v1.8.4) - 2024-08-30

### Fix

* Propagate row_section in tables ([#57](https://github.com/DS4SD/docling/issues/57)) ([`de85e46`](https://github.com/DS4SD/docling/commit/de85e46ced293bdef7957f72fff301fec178cc94))

### Documentation

* Add instructions for cpu-only installation ([#56](https://github.com/DS4SD/docling/issues/56)) ([`a8a60d5`](https://github.com/DS4SD/docling/commit/a8a60d52b17fc25e71a421d4f89240bc7f02e154))

## [v1.8.3](https://github.com/DS4SD/docling/releases/tag/v1.8.3) - 2024-08-28

### Fix

* Table cells overlap and model warnings ([#53](https://github.com/DS4SD/docling/issues/53)) ([`f49ee82`](https://github.com/DS4SD/docling/commit/f49ee825c3b95ffd5de29242aec764b074c773f7))

## [v1.8.2](https://github.com/DS4SD/docling/releases/tag/v1.8.2) - 2024-08-27

### Fix

* Refine conversion result ([#52](https://github.com/DS4SD/docling/issues/52)) ([`e46a66a`](https://github.com/DS4SD/docling/commit/e46a66a17606a26f351b798ecf4fdeae71465f9c))

### Documentation

* Update interface in README ([#50](https://github.com/DS4SD/docling/issues/50)) ([`fe817b1`](https://github.com/DS4SD/docling/commit/fe817b11d730c55d48b6a60fc4e6f173da51a66b))

## [v1.8.1](https://github.com/DS4SD/docling/releases/tag/v1.8.1) - 2024-08-26

### Fix

* Align output formats ([#49](https://github.com/DS4SD/docling/issues/49)) ([`8cc147b`](https://github.com/DS4SD/docling/commit/8cc147bc56753144915709a48b08830d0c3ad44e))

## [v1.8.0](https://github.com/DS4SD/docling/releases/tag/v1.8.0) - 2024-08-23

### Feature

* Page-level error reporting from PDF backend, introduce PARTIAL_SUCCESS status ([#47](https://github.com/DS4SD/docling/issues/47)) ([`a294b7e`](https://github.com/DS4SD/docling/commit/a294b7e64a4d66ebb9fd328c084e5f74647805ee))

## [v1.7.1](https://github.com/DS4SD/docling/releases/tag/v1.7.1) - 2024-08-23

### Fix

* Better raise exception when a page fails to parse ([#46](https://github.com/DS4SD/docling/issues/46)) ([`8808463`](https://github.com/DS4SD/docling/commit/8808463cecd7ff3a92bd99d2e3d65fd248672c9e))
* Upgrade docling-parse to 1.1.1, safety checks for failed parse on pages ([#45](https://github.com/DS4SD/docling/issues/45)) ([`7e84533`](https://github.com/DS4SD/docling/commit/7e845332992ab37386daee087573773051bfd065))

## [v1.7.0](https://github.com/DS4SD/docling/releases/tag/v1.7.0) - 2024-08-22

### Feature

* Upgrade docling-parse PDF backend and interface to use page-by-page parsing ([#44](https://github.com/DS4SD/docling/issues/44)) ([`a8c6b29`](https://github.com/DS4SD/docling/commit/a8c6b29a67ca303d6eec3fabb6b5e75ad5a7676d))

## [v1.6.3](https://github.com/DS4SD/docling/releases/tag/v1.6.3) - 2024-08-22

### Fix

* Usage of bytesio with docling-parse ([#43](https://github.com/DS4SD/docling/issues/43)) ([`fac5745`](https://github.com/DS4SD/docling/commit/fac5745dc846281bfae64bc631658bb2a2c90982))

## [v1.6.2](https://github.com/DS4SD/docling/releases/tag/v1.6.2) - 2024-08-22

### Fix

* Remove [ocr] extra to fix wheel install ([#42](https://github.com/DS4SD/docling/issues/42)) ([`6995268`](https://github.com/DS4SD/docling/commit/69952682edd014a3f252e9c87edffa7c34f1033b))

## [v1.6.1](https://github.com/DS4SD/docling/releases/tag/v1.6.1) - 2024-08-21

### Fix

* Add scipy as dependency ([#40](https://github.com/DS4SD/docling/issues/40)) ([`f19871a`](https://github.com/DS4SD/docling/commit/f19871a5a164b5369da10f7753d7c7da7fde35cc))

## [v1.6.0](https://github.com/DS4SD/docling/releases/tag/v1.6.0) - 2024-08-20

### Feature

* Add adaptive OCR, factor out treatment of OCR areas and cell filtering ([#38](https://github.com/DS4SD/docling/issues/38)) ([`e94d317`](https://github.com/DS4SD/docling/commit/e94d317c022d2b916332d43cdc2aa90fd4738df9))

## [v1.5.0](https://github.com/DS4SD/docling/releases/tag/v1.5.0) - 2024-08-20

### Feature

* Allow computing page images on-demand with scale and cache them ([#36](https://github.com/DS4SD/docling/issues/36)) ([`78347bf`](https://github.com/DS4SD/docling/commit/78347bf679c393378eab0bd383929fced88afeae))

### Documentation

* Add technical paper ref ([#37](https://github.com/DS4SD/docling/issues/37)) ([`a13114b`](https://github.com/DS4SD/docling/commit/a13114bafdcf4b62eb97df32cbfaf5695596b77c))

## [v1.4.0](https://github.com/DS4SD/docling/releases/tag/v1.4.0) - 2024-08-14

### Feature

* Update parser with bytesio interface and set as new default backend ([#32](https://github.com/DS4SD/docling/issues/32)) ([`90dd676`](https://github.com/DS4SD/docling/commit/90dd676422f87584395a8949fa842fc9a6bdbd19))

### Fix

* Allow newer torch versions ([#34](https://github.com/DS4SD/docling/issues/34)) ([`349b0e9`](https://github.com/DS4SD/docling/commit/349b0e914f7194ee778571a7189b7eaff6f5966a))

## [v1.3.0](https://github.com/DS4SD/docling/releases/tag/v1.3.0) - 2024-08-12

### Feature

* Output page images and extracted bbox ([#31](https://github.com/DS4SD/docling/issues/31)) ([`63d80ed`](https://github.com/DS4SD/docling/commit/63d80edca2fa4e64a07d8b00172d563d81ecb781))

## [v1.2.1](https://github.com/DS4SD/docling/releases/tag/v1.2.1) - 2024-08-07

### Fix

* Update (vuln) deps ([#29](https://github.com/DS4SD/docling/issues/29)) ([`79ef8d2`](https://github.com/DS4SD/docling/commit/79ef8d2f2f6732f94c6777877ac9d0a45915ac84))
* Type of path_or_stream in PdfDocumentBackend ([#28](https://github.com/DS4SD/docling/issues/28)) ([`794b20a`](https://github.com/DS4SD/docling/commit/794b20a50ad089b39d4a4a84dcd826935b2b83ed))

### Documentation

* Improve examples ([#27](https://github.com/DS4SD/docling/issues/27)) ([`9550db8`](https://github.com/DS4SD/docling/commit/9550db8e64c4d638a429be33c10f10f18871f795))

## [v1.2.0](https://github.com/DS4SD/docling/releases/tag/v1.2.0) - 2024-08-07

### Feature

* Introducing docling_backend ([#26](https://github.com/DS4SD/docling/issues/26)) ([`b8f5e38`](https://github.com/DS4SD/docling/commit/b8f5e38a8c8b3fd734fa119cae216a3da0b363f7))

## [v1.1.2](https://github.com/DS4SD/docling/releases/tag/v1.1.2) - 2024-07-31

### Fix

* Set page number using 1-based indexing ([#22](https://github.com/DS4SD/docling/issues/22)) ([`d2d9543`](https://github.com/DS4SD/docling/commit/d2d9543415d37c54add917803b96d9959dc4d2cc))

## [v1.1.1](https://github.com/DS4SD/docling/releases/tag/v1.1.1) - 2024-07-30

### Fix

* Correct text extraction for table cells ([#21](https://github.com/DS4SD/docling/issues/21)) ([`f4bf3d2`](https://github.com/DS4SD/docling/commit/f4bf3d25b955b71729833a18aa3a5b643fecfa75))

## [v1.1.0](https://github.com/DS4SD/docling/releases/tag/v1.1.0) - 2024-07-26

### Feature

* Add simplified single-doc conversion ([#20](https://github.com/DS4SD/docling/issues/20)) ([`d603137`](https://github.com/DS4SD/docling/commit/d60313738340c20f9af64dfe51e28b7670ff64ef))

## [v1.0.2](https://github.com/DS4SD/docling/releases/tag/v1.0.2) - 2024-07-24

### Fix

* Add easyocr to main deps for valid extra ([#19](https://github.com/DS4SD/docling/issues/19)) ([`54b3dda`](https://github.com/DS4SD/docling/commit/54b3dda141fc09e8c17ba4cb301d0c4394b680d8))

## [v1.0.1](https://github.com/DS4SD/docling/releases/tag/v1.0.1) - 2024-07-24

### Fix

* Expose ocr as extra ([#18](https://github.com/DS4SD/docling/issues/18)) ([`b0725e0`](https://github.com/DS4SD/docling/commit/b0725e0aa693058b4962efa69730777dbe1d5bec))

## [v1.0.0](https://github.com/DS4SD/docling/releases/tag/v1.0.0) - 2024-07-18

### Feature

* V1.0.0 release ([#16](https://github.com/DS4SD/docling/issues/16)) ([`71c3a9c`](https://github.com/DS4SD/docling/commit/71c3a9c8cde5b3a8884430eddcb33a9fbd7bf354))

### Breaking

* v1.0.0 release ([#16](https://github.com/DS4SD/docling/issues/16)) ([`71c3a9c`](https://github.com/DS4SD/docling/commit/71c3a9c8cde5b3a8884430eddcb33a9fbd7bf354))

## [v0.4.0](https://github.com/DS4SD/docling/releases/tag/v0.4.0) - 2024-07-17

### Feature

* Optimize table extraction quality, add configuration options ([#11](https://github.com/DS4SD/docling/issues/11)) ([`e9526bb`](https://github.com/DS4SD/docling/commit/e9526bb11e21dc85c787af5c38e6f77eaca05f69))

## [v0.3.1](https://github.com/DS4SD/docling/releases/tag/v0.3.1) - 2024-07-17

### Fix

* Missing type for default values ([#12](https://github.com/DS4SD/docling/issues/12)) ([`d1d1724`](https://github.com/DS4SD/docling/commit/d1d1724537d6a1f37591cdea44052207caae2ee2))

### Documentation

* Reflect supported Python versions, add badges ([#10](https://github.com/DS4SD/docling/issues/10)) ([`2baa35c`](https://github.com/DS4SD/docling/commit/2baa35c548dd6d15dba449eb1dc707f8f08c0a2a))

## [v0.3.0](https://github.com/DS4SD/docling/releases/tag/v0.3.0) - 2024-07-17

### Feature

* Enable python 3.12 support by updating glm ([#8](https://github.com/DS4SD/docling/issues/8)) ([`fb72688`](https://github.com/DS4SD/docling/commit/fb72688ff7413083c864fe62d2dbfc420c1e5268))

### Documentation

* Add setup with pypi to Readme ([#7](https://github.com/DS4SD/docling/issues/7)) ([`2803222`](https://github.com/DS4SD/docling/commit/2803222ee1708481c779d435dbf1c031929d3cf6))

## [v0.2.0](https://github.com/DS4SD/docling/releases/tag/v0.2.0) - 2024-07-16

### Feature

* Build with ci ([#6](https://github.com/DS4SD/docling/issues/6)) ([`b1479cf`](https://github.com/DS4SD/docling/commit/b1479cf4ecf8a586703b31c7cf6917b3293c6a85))
