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
