# Data Dictionary

All data is synthetic. Company names, phone numbers, emails and websites are generated. Any match with a real company is a coincidence.

Encoding is UTF-8. Dates are ISO 8601.

## companies.csv

One row per company registration on the platform. The same real company may be registered more than once.

| Column | Notes |
|---|---|
| company_id | Row ID, e.g. CMP-00001. Unique per row, not per real company. |
| company_name | As entered by the company. |
| country | Country name. Spelling varies. |
| city | City name. Old and new names both occur. |
| address | May be blank. |
| website, email, phone | Formats vary. May be blank. |
| company_type | Self-declared, e.g. Manufacturer, Importer, Trader. |
| year_established, employee_range | May be blank. |
| certifications | Free text list. Separators and spellings vary. |
| about | Free text profile. May be blank. |
| registered_on | Date the row was created on the platform. |

## products.csv

Listings created by sellers. Each listing belongs to one company_id.

| Column | Notes |
|---|---|
| product_id | e.g. PRD-000001 |
| company_id | Links to companies.csv |
| title, description | Free text. No HS code is given. Some listings are too vague to classify. |
| moq, moq_unit | Minimum order quantity |
| price_usd_min, price_usd_max, price_unit | Indicative price range |
| listed_on | Date listed |

## shipments.csv

Import and export records from customs-style sources. October 2024 to September 2026.

| Column | Notes |
|---|---|
| shipment_id | Row ID |
| bill_of_lading | Carrier B/L number |
| shipment_date | Date |
| shipper_name, consignee_name | Names as filed. No company IDs. Formatting varies. |
| shipper_country, consignee_country | Country names. Spelling varies. |
| origin_country | Where the goods were produced. Can differ from shipper_country. |
| destination_country | Country name |
| port_of_loading, port_of_discharge | Port names, aliases or UN/LOCODEs |
| hs_code | 4, 6 or 8 digits, sometimes formatted or blank |
| goods_description | Free text |
| quantity, quantity_unit | Units vary for the same product |
| value_usd | Declared value. Sometimes blank or zero. |
| incoterm | FOB, CIF, CFR and others |

## rfqs.json

A JSON array. Each item has rfq_id, buyer_company_id, created_at, status and text. The text is written by buyers in free form.

## interactions.csv

Platform events from October 2025 to October 2026.

| Column | Notes |
|---|---|
| event_id, event_time | |
| event_type | profile_view, product_view, chat_request, chat_accepted, chat_rejected, quotation_sent, quotation_accepted, rfq_response |
| actor_company_id | Company that performed the action |
| target_company_id | Company the action was aimed at |
| product_id | Set for product_view |
| rfq_id | Set for rfq_response |

## hs_codes.csv

The HS codes used in this dataset, at 6 digits. The category column defines "category" for Task 3b.

## er_labels.csv

200 labelled pairs of company_id values. is_same_entity is 1 if both rows are the same real company.

## product_hs_labels.csv

100 labelled products. hs_code is the correct 6-digit code, or UNMAPPABLE if the listing cannot be classified.

## Known issues

These are intentional. Handling them is part of the task.

- Duplicate company registrations with different names, contacts and cities.
- Similar names that belong to different companies.
- Inconsistent country, city, port and unit names.
- HS codes at the wrong length or in the wrong format.
- Shipment parties that are not companies, or that are not the real buyer.
- Repeated shipment records.
- Goods shipped by a company in one country but produced in another.
