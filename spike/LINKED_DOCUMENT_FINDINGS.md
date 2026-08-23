# Linked-Document Fallback Feasibility Findings

**Verdict: FAIL**

Live window: 2024-04-01 to 2026-08-23. Companies scanned: 21. Unreviewed records: 0.

| Metric | Result |
|---|---:|
| Confirmed cover letters | 33 |
| Confirmed controls | 30 |
| Cover-letter issuers | 5 |
| Cover-letter categories | 3 |
| Detection recall | 100.0% |
| False positives | 0 |
| Resolution rate | 54.5% |
| Exact-host adapters used | 1 |
| Normal-path external requests | 0 |

## Decision

The feasibility gate **fails** because only 18 of 33 confirmed cover letters resolved to a substantive PDF (54.5%), below the required 80%. Every other gate condition passed: 100% detection recall, zero false positives across 30 substantive controls, all three required issuers resolved at least once, one exact-host adapter, and zero external requests for normal filings.

The 15 honest failures were: four Maruti letters whose PDF extraction did not retain a usable URL; nine historical HDFC/L&T landing-page cases without one uniquely selectable static PDF; one HDFC link returning HTTP 403; and one Adani link returning an HTML not-found page instead of a PDF.

This result does not support broad production rollout. Detection is feasible and lightweight, while general automatic resolution needs a narrower policy or more issuer-specific machinery than this gate allowed.

## Cases

| Company | Date | Type | Pages | Detected | Review | Resolution | Source |
|---|---|---|---:|---|---|---|---|
| KFin Technologies | 2026-06-29 | annual-reports | 1 | True | cover | resolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/68232f64-9007-48de-a073-97b65083e365.pdf) |
| KFin Technologies | 2025-08-05 | annual-reports | 2 | True | cover | resolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/3c0bb8eb-3ef6-4e59-bb6d-cf4e741c5721.pdf) |
| Maruti Suzuki | 2026-08-06 | concalls | 1 | True | cover | unresolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/e5ed553b-9881-4cd9-a131-370360446a83.pdf) |
| Maruti Suzuki | 2026-05-04 | concalls | 1 | True | cover | resolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/cb094054-0db2-49ed-b602-b4872110fc68.pdf) |
| Maruti Suzuki | 2026-02-02 | concalls | 1 | True | cover | resolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/1d7965cf-ea8d-4a59-b2d1-30d9c0c4969f.pdf) |
| Maruti Suzuki | 2025-11-03 | concalls | 1 | True | cover | resolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/55f7cee9-19ee-40fb-9041-6445ea307574.pdf) |
| Maruti Suzuki | 2025-08-06 | concalls | 1 | True | cover | resolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/52a4a2af-bc3c-4598-8c7d-0732fcbea876.pdf) |
| Maruti Suzuki | 2025-05-01 | concalls | 1 | True | cover | unresolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/fcd33029-a973-4fb2-beb0-6d7c96215eb9.pdf) |
| Maruti Suzuki | 2025-02-04 | concalls | 1 | True | cover | unresolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/c344a56f-6f41-400a-b86f-3caadf8d6f5c.pdf) |
| Maruti Suzuki | 2024-11-05 | concalls | 1 | True | cover | unresolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/851557d5-d151-484d-9dfc-33b356e45e4b.pdf) |
| Maruti Suzuki | 2024-08-06 | concalls | 1 | True | cover | resolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/d9edfffd-78a6-4a67-916f-77a9dff5ee2f.pdf) |
| Maruti Suzuki | 2024-05-03 | concalls | 1 | True | cover | resolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/2ba1aa47-f970-48d2-982d-923399e772d9.pdf) |
| HDFC Bank | 2026-01-17 | investor-ppts | 1 | True | cover | resolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/aab7c9ec-6594-4434-913d-00660c6bd766.pdf) |
| HDFC Bank | 2025-10-18 | investor-ppts | 1 | True | cover | unresolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/bb5441ee-cf3c-4cfc-a034-b9587c476f20.pdf) |
| HDFC Bank | 2025-04-19 | investor-ppts | 1 | True | cover | unresolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/e19ba89d-02a3-48aa-be3d-7ab0b6d200e4.pdf) |
| HDFC Bank | 2025-01-22 | investor-ppts | 1 | True | cover | unresolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/b4043b6a-465f-4bef-a9ea-ca3a72573cdb.pdf) |
| Larsen & Toubro | 2026-08-03 | concalls | 1 | True | cover | resolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/503fa772-d48c-49d5-9d21-0727e91591b0.pdf) |
| Larsen & Toubro | 2026-02-03 | concalls | 1 | True | cover | unresolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/0d9f00a9-945d-46b3-96d9-3c730828f1d7.pdf) |
| Larsen & Toubro | 2025-11-04 | concalls | 1 | True | cover | unresolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/492d75b5-a335-4251-9ece-e36f21e0e34d.pdf) |
| Larsen & Toubro | 2025-08-04 | concalls | 1 | True | cover | unresolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/b041377b-c512-43bb-bf98-3f6a2a551128.pdf) |
| Larsen & Toubro | 2025-05-14 | concalls | 1 | True | cover | unresolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/006d9af3-8ffc-4918-87e8-ab6e045a0c19.pdf) |
| Larsen & Toubro | 2024-11-04 | concalls | 1 | True | cover | unresolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/6c5e2aeb-4512-43f4-8f44-7d7aacf28710.pdf) |
| Larsen & Toubro | 2024-07-30 | concalls | 1 | True | cover | unresolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/5225fba1-48c3-4850-9c9e-3b8891b22c9d.pdf) |
| Larsen & Toubro | 2024-05-13 | concalls | 1 | True | cover | unresolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/7ad281cc-d86a-4386-92ff-82f3bdfb3ae0.pdf) |
| Adani Enterprises | 2026-08-05 | concalls | 1 | True | cover | resolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/e0068632-9672-4f42-9812-13a0e0b3ef63.pdf) |
| Adani Enterprises | 2026-05-07 | concalls | 1 | True | cover | resolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/4eee4331-589a-4b61-9b2e-b0adf66711b7.pdf) |
| Adani Enterprises | 2026-02-09 | concalls | 1 | True | cover | unresolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/cabc5b1f-2ba0-43f5-84fa-5f820e0c4e1c.pdf) |
| Adani Enterprises | 2025-11-10 | concalls | 1 | True | cover | resolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/5a639c02-968a-4206-a4e6-39c9b3219bd9.pdf) |
| Adani Enterprises | 2025-08-05 | concalls | 1 | True | cover | resolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/e15fe661-864e-453a-905f-9a8a26e3583c.pdf) |
| Adani Enterprises | 2025-05-07 | concalls | 1 | True | cover | resolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/1547dc88-edf8-4ba5-8526-184d835ce26a.pdf) |
| Adani Enterprises | 2025-02-04 | concalls | 1 | True | cover | resolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/e54ea6c1-6868-4962-a793-e4a7bf4c0851.pdf) |
| Adani Enterprises | 2024-11-05 | concalls | 1 | True | cover | resolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/0c701a2f-89bc-44cd-b304-f133eb4c3c0a.pdf) |
| Adani Enterprises | 2024-08-07 | concalls | 1 | True | cover | resolved | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/2ebc0f2a-ac2d-4281-b49a-41a092c4e856.pdf) |
| KFin Technologies | 2026-07-24 | quarterly | 13 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/619a4d4d-b631-4bf0-8b92-e2236898b811.pdf) |
| KFin Technologies | 2026-02-13 | quarterly | 13 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/9036a4a8-333a-4a8a-80ae-3042f3934f57.pdf) |
| KFin Technologies | 2025-10-27 | quarterly | 14 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/c1740eb9-daca-46ec-9ca0-1fc4b7b07f84.pdf) |
| KFin Technologies | 2025-07-24 | quarterly | 12 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/90a8dd46-0327-4901-94a7-6370e020c7fc.pdf) |
| KFin Technologies | 2025-01-23 | quarterly | 11 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/df594818-0a5a-4348-ba30-6bb98401c2b8.pdf) |
| KFin Technologies | 2024-10-28 | quarterly | 13 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/0748a68c-2e6f-42ae-9326-c1ca5287f311.pdf) |
| KFin Technologies | 2024-07-26 | quarterly | 11 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/e66be376-61aa-484d-8fcb-c78c833d7ba3.pdf) |
| Maruti Suzuki | 2026-07-31 | investor-ppts | 14 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/4b7f0db8-b33e-4a14-bb96-542978860d78.pdf) |
| Maruti Suzuki | 2025-07-31 | investor-ppts | 14 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/fb1d3824-d661-4143-b061-9964bf79d1b3.pdf) |
| Maruti Suzuki | 2025-07-31 | quarterly | 10 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/137cfadf-5b68-453d-b006-18b67f7b250e.pdf) |
| Maruti Suzuki | 2025-01-29 | quarterly | 8 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/77832613-34c2-461f-8294-c536b678f001.pdf) |
| Maruti Suzuki | 2024-07-31 | quarterly | 8 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/10dcc4ae-bf65-4091-8a4b-9ba6d463843e.pdf) |
| Tanla Platforms | 2026-07-22 | quarterly | 8 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/947e7695-98f5-431f-ac09-59280815041d.pdf) |
| Tanla Platforms | 2026-01-22 | quarterly | 8 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/e4b6af99-145d-497b-bfd8-a3882714065b.pdf) |
| Tanla Platforms | 2025-10-17 | quarterly | 10 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/060b2fda-39e5-4aac-abb7-f4c80e2b3b8f.pdf) |
| Tanla Platforms | 2025-07-28 | concalls | 11 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/0fa90d17-3b9e-4255-9514-8c9e6e439383.pdf) |
| Tanla Platforms | 2025-07-24 | quarterly | 8 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/6390d4ec-d2ef-4e4a-921b-73fe3f81ff03.pdf) |
| Tanla Platforms | 2025-05-01 | concalls | 13 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/f0a9cb80-4e1a-4281-be04-875635592282.pdf) |
| Tanla Platforms | 2025-01-28 | concalls | 12 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/a35ee3ad-f67c-4711-8859-bc7b369eb130.pdf) |
| Tanla Platforms | 2025-01-21 | quarterly | 11 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/e43546e9-79ec-4749-aa8b-089e18adcd72.pdf) |
| Tanla Platforms | 2024-10-17 | quarterly | 10 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/4f0478c2-ae5f-468a-af5d-4565b1c4443d.pdf) |
| Tanla Platforms | 2024-07-18 | quarterly | 10 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/cdcf7df6-62af-4ac8-8562-629fec8fcb15.pdf) |
| Kaynes Technology | 2025-01-27 | quarterly | 11 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/8c700749-9337-4ca7-b49c-4df727708a1e.pdf) |
| Kaynes Technology | 2025-01-27 | quarterly | 11 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/404cef82-4706-426d-bac0-81a21553f5ca.pdf) |
| Eternal | 2026-07-22 | quarterly | 12 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/1c70b7a0-029b-44b6-bb04-c5baadf20fb9.pdf) |
| Eternal | 2025-01-20 | quarterly | 11 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/189f6577-91c3-4738-abf1-dc3f9c68de6b.pdf) |
| Eternal | 2024-08-01 | quarterly | 10 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/9f31efcc-2cef-4026-82de-aaccc3906df5.pdf) |
| State Bank of India | 2026-02-07 | quarterly | 3 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/7FCD5639-F021-4635-9310-B94DCECCBC78-135253.pdf) |
| Hindustan Unilever | 2025-07-31 | quarterly | 12 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/e9f65f15-c05a-40bf-a288-f82f36788e71.pdf) |
| Hindustan Unilever | 2025-01-22 | quarterly | 12 | False | control | substantive | [BSE](https://www.bseindia.com/xml-data/corpfiling/AttachHis/980fa38f-346b-4865-8685-aa7a0c52e659.pdf) |
