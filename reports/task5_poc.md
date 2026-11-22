# POC test set

Produced by `PYTHONPATH=src python -m tradekg.poc`. The Streamlit app (`streamlit run app.py`) calls the same functions.

No language model is called. Extraction is the phrase table plus the closed country, port, and certificate lists. A search sentence can also set a required origin or a manufacturer filter. Those filters only drop sellers the ranker already returned. Cost per query: $0.

Search is ranked as of 2026-09-30, the latest shipment date in the extract. A posted RFQ that already exists is ranked as of its own `created_at`, and the buyer who posted it is excluded.

## Search

### Q1

Frozen vannamei shrimp suppliers from India that already ship to the United States

- Product: Frozen vannamei shrimp suppliers from India that already ship to the United States → HS 030617 (Agriculture & Food), quantity None
- Destination: United States
- Preferred origin: India
- Excluded origin: not stated
- Certificates: not stated

Required origin India: each seller has at least one shipment of this code from there. 16 sellers remain.
Relaxed: nothing. Ranked as of 2026-09-30. 16 sellers in the set, 10 shown.

1. Sri Saraswati Seafoods Impex LLP (ENT-01398, manufacturer)
   Exported HS 030617 to United States 6 times in the 12 months before this request. Shipments of this code originated in India.
   No listing is classified as this code.
2. Kamdhenu Agro Pvt Ltd (ENT-00452, manufacturer)
   Exported HS 030617 to United States 2 times in the 12 months before this request. Shipments of this code originated in India.
   Listings: Export Quality Frozen headless shell-on vannamei (030617)
3. Om Umiya Agri Foods Pvt Ltd (ENT-02004, manufacturer)
   Exported HS 030617 to United States once in the 12 months before this request. Shipments of this code originated in India.
   Listings: Frozen PUD shrimp for Export (030617)
4. Wessex Commodities Ltd (ENT-03725, mixed)
   Exported HS 030617 to United States 3 times in the 12 months before this request. Shipments of this code originated in India.
   Listings: High Quality Frozen PUD shrimp (OEM available) (030617)
5. Maa Saraswati Seafoods Exim (ENT-02794, manufacturer)
   Exported HS 030617 to United States 2 times in the 12 months before this request. Shipments of this code originated in India.
   No listing is classified as this code.
6. Shubh Foods Enterprises LLP (ENT-00258, manufacturer)
   Exported HS 030617 to United States 2 times in the 12 months before this request. Shipments of this code originated in India.
   No listing is classified as this code.
7. Arabian Link Provisions FZE (ENT-01506, mixed)
   Exported HS 030617 to United States 2 times in the 12 months before this request. Shipments of this code originated in India.
   Listings: Wholesale Frozen vannamei shrimp for Export (030617)
8. Maa Mahalaxmi Agro Products Exports (ENT-01097, manufacturer)
   Exported HS 030617 to United States once in the 12 months before this request. Shipments of this code originated in India.
   Listings: Export Quality IQF peeled deveined shrimp (030617)
9. Bright Seafoods Exim Pvt Ltd (ENT-03062, manufacturer)
   Exported HS 030617 to United States once. Shipments of this code originated in India.
   Listings: Export Quality Frozen vannamei shrimp - Bulk Supply (030617)
10. Al Otaibi Commodities Trading Est. (ENT-00784, mixed)
   Exported HS 030617 to United States once in the 12 months before this request. Shipments of this code originated in India.
   Listings: High Quality Frozen headless shell-on vannamei (OEM available) (030617)

### Q2

HDPE pipe grade resin, Saudi origin, ISO 9001 certified supplier

- Product: HDPE pipe grade resin, Saudi origin, ISO 9001 certified supplier → HS 390120 (Chemicals, Plastics & Personal Care), quantity None
- Destination: not stated
- Preferred origin: Saudi Arabia
- Excluded origin: not stated
- Certificates: ISO_9001

Required origin Saudi Arabia: each seller has at least one shipment of this code from there. 6 sellers remain.
Relaxed: nothing. Ranked as of 2026-09-30. 6 sellers in the set, 6 shown.

1. Al Fajr Agri Inputs LLC (ENT-01081, mixed)
   Exported HS 390120 12 times. Shipments of this code originated in Saudi Arabia. Holds ISO 9001.
   Listings: Export Quality High density polyethylene (390120); High Quality High density polyethylene for Export (390120)
2. Silver Sands Commodities Trading FZE (ENT-02077, mixed)
   Exported HS 390120 9 times. Shipments of this code originated in Saudi Arabia. Holds ISO 9001.
   No listing is classified as this code.
3. Al Dossary Plastics Co. (ENT-02070, manufacturer)
   Exported HS 390120 4 times. Shipments of this code originated in Saudi Arabia. Holds ISO 9001.
   Listings: Premium HDPE pipe grade PE100 for Export (390120)
4. Al Shehri Fertilizers Est. (ENT-00297, manufacturer)
   Exported HS 390120 3 times. Shipments of this code originated in Saudi Arabia. Holds ISO 9001.
   Listings: Best Price HDPE pipe grade PE100 for Export (390120)
5. Najd Polymers Co. (ENT-03421, manufacturer)
   Exported HS 390120 4 times. Shipments of this code originated in Saudi Arabia. Holds ISO 9001.
   Listings: Premium HDPE granules for Export (390120); Best Price HDPE blow moulding grade (390120)
6. Al Bayan Plastics LLC (ENT-02169, trader)
   Exported HS 390120 once. Shipments of this code originated in Saudi Arabia. Holds ISO 9001.
   No listing is classified as this code.

### Q3

Brake pads manufacturer with IATF 16949, no China origin

- Product: Brake pads manufacturer with IATF 16949, no China origin → HS 870830 (Automotive), quantity None
- Destination: not stated
- Preferred origin: not stated
- Excluded origin: China
- Certificates: IATF_16949

Limited to manufacturers and companies that both manufacture and trade. 7 sellers were omitted because they have no shipment of this code from outside the excluded origin. A listing alone does not establish origin. 8 sellers remain.
Relaxed: nothing. Ranked as of 2026-09-30. 8 sellers in the set, 8 shown.

1. Sri Saraswati Automotive Pvt Ltd (ENT-02913, manufacturer)
   Exported HS 870830 13 times. Holds IATF 16949.
   Listings: Premium Brake calipers (870830); Export Quality Brake pads (OEM available) (870830)
2. Jai Balaji Auto Parts Impex Pvt Ltd (ENT-02953, manufacturer)
   Exported HS 870830 12 times. Holds IATF 16949.
   Listings: Premium Brake pads - Bulk Supply (870830)
3. Shree Mahalaxmi Automotive Pvt Ltd (ENT-02010, manufacturer)
   Exported HS 870830 8 times. Holds IATF 16949.
   Listings: High Quality Brake discs (870830)
4. Northstar Motors LLC (ENT-00553, mixed)
   Exported HS 870830 4 times. Holds IATF 16949.
   No listing is classified as this code.
5. Shree Gayatri Motors Industries Pvt Ltd (ENT-00699, manufacturer)
   Exported HS 870830 3 times. Holds IATF 16949.
   No listing is classified as this code.
6. Al Noor Commodities Trading LLC (ENT-03485, mixed)
   Exported HS 870830 once. Holds IATF 16949.
   Listings: Brake calipers (870830)
7. Sri Bhagwati Auto Components Pvt Ltd (ENT-01866, manufacturer)
   Exported HS 870830 once. Holds IATF 16949.
   Listings: Disc brake rotors (OEM available) (870830); Disc brake rotors (OEM available) (870830)
8. Mercia Trading Ltd (ENT-00506, mixed)
   Exported HS 870830 once. Holds IATF 16949.
   No listing is classified as this code.

### Q4

Porcelain floor tiles 600x600 for a project in Saudi Arabia, need suppliers with experience shipping to KSA

- Product: Porcelain floor tiles 600x600 for a project in Saudi Arabia, need suppliers with experience shipping to KSA → HS 690721 (Construction Materials), quantity None
- Destination: Saudi Arabia
- Preferred origin: not stated
- Excluded origin: not stated
- Certificates: not stated

32 sellers match the extracted constraints.
Relaxed: nothing. Ranked as of 2026-09-30. 32 sellers in the set, 10 shown.

1. Heartland Group Corp. (ENT-01179, trader)
   Exported HS 690721 to Saudi Arabia 5 times in the 12 months before this request.
   Listings: Export Quality Vitrified tiles 600x600 (690721)
2. Greco Ceramiche S.r.l. (ENT-03012, manufacturer)
   Exported HS 690721 to Saudi Arabia 4 times in the 12 months before this request.
   Listings: Premium Double charge vitrified tiles | Italy Origin (690721)
3. Serendib General Trading (Pvt) Ltd (ENT-02093, mixed)
   Exported HS 690721 to Saudi Arabia 3 times in the 12 months before this request.
   Listings: Glazed porcelain tiles for Export (690721); Wholesale GVT tiles 800x1600 (690721)
4. Rossi Marmi S.r.l. (ENT-01958, manufacturer)
   Exported HS 690721 to Saudi Arabia 3 times in the 12 months before this request.
   Listings: Export Quality Double charge vitrified tiles | Italy Origin (690721)
5. Narmada Granite & Marble Exim (ENT-02814, manufacturer)
   Exported HS 690721 to Saudi Arabia 3 times in the 12 months before this request.
   Listings: High Quality GVT tiles 800x1600 (690721); Premium Double charge vitrified tiles (690721)
6. Vindhya Tiles Overseas LLP (ENT-00153, manufacturer)
   Exported HS 690721 to Saudi Arabia 3 times in the 12 months before this request.
   Listings: Wholesale GVT tiles 800x1600 (OEM available) (690721)
7. Maa Ram Ceramics LLP (ENT-00906, manufacturer)
   Exported HS 690721 to Saudi Arabia 3 times in the 12 months before this request.
   No listing is classified as this code.
8. Om Siddhivinayak Tiles Exim (ENT-00439, manufacturer)
   Exported HS 690721 to Saudi Arabia 2 times in the 12 months before this request.
   Listings: Premium Glazed porcelain tiles (690721); Premium Glazed porcelain tiles for Export (690721)
9. Om Sai Stones Pvt Ltd (ENT-03668, manufacturer)
   Exported HS 690721 to Saudi Arabia 3 times in the 12 months before this request.
   No listing is classified as this code.
10. Shanghai Anxiang Building Materials Co., Ltd. (ENT-04075, manufacturer)
   Exported HS 690721 to Saudi Arabia 2 times in the 12 months before this request.
   Listings: Double charge vitrified tiles (OEM available) (690721)

### Q5

Who sells 1121 basmati rice and what is the going price by origin?

- Product: Who sells 1121 basmati rice and what is the going price by origin? → HS 100630 (Agriculture & Food), quantity None
- Destination: not stated
- Preferred origin: not stated
- Excluded origin: not stated
- Certificates: not stated

100 sellers match the extracted constraints.
Relaxed: nothing. Ranked as of 2026-09-30. 100 sellers in the set, 10 shown.

1. Crystal Agri Foods Impex (ENT-03404, manufacturer)
   Exported HS 100630 51 times.
   No listing is classified as this code.
2. Modern Foods Impex (ENT-03938, manufacturer)
   Exported HS 100630 47 times.
   Listings: Pusa basmati rice (100630)
3. Tanjung Trading Sdn Bhd (ENT-03293, trader)
   Exported HS 100630 28 times.
   Listings: High Quality IR64 parboiled rice 5% broken (100630)
4. An Phat Agricultural Products Joint Stock Company (ENT-01023, manufacturer)
   Exported HS 100630 39 times.
   No listing is classified as this code.
5. Gulf Star General Trading LLC (ENT-02940, mixed)
   Exported HS 100630 27 times.
   Listings: High Quality Jasmine rice - Bulk Supply (100630)
6. Prime Spices Pvt Ltd (ENT-01341, manufacturer)
   Exported HS 100630 22 times.
   Listings: Best Price Long grain white rice - Bulk Supply (100630); High Quality Sona masoori rice | India Origin (100630); Jasmine rice - Bulk Supply (100630)
7. Nam Viet Seafood Company Limited (ENT-00317, manufacturer)
   Exported HS 100630 21 times.
   Listings: High Quality Sona masoori rice (100630); Wholesale 1121 basmati rice (OEM available) (100630)
8. Kingsway Food Distributors Ltd (ENT-01761, trader)
   Exported HS 100630 14 times.
   Listings: Pusa basmati rice - Bulk Supply (100630)
9. Dune Line Foodstuff LLC (ENT-02660, mixed)
   Exported HS 100630 21 times.
   Listings: Export Quality IR64 parboiled rice 5% broken (OEM available) (100630)
10. Shri Krishna Agri Foods LLP (ENT-03464, manufacturer)
   Exported HS 100630 13 times.
   Listings: Wholesale 1121 basmati rice - Bulk Supply (100630); Premium Long grain white rice (100630)

Traded unit price for HS 100630 (Semi-milled or wholly milled rice, whether or not polished or glazed), USD per MT. 858 bills kept, 0 dropped for a different dimension.

By origin:

| Origin | Bills | Median | P25 | P75 |
| --- | ---: | ---: | ---: | ---: |
| India | 539 | 736.47 | 556.54 | 906.03 |
| Vietnam | 168 | 739.63 | 598.27 | 897.6 |
| Pakistan | 64 | 763.61 | 571.45 | 891.25 |
| Malaysia | 38 | 839.6 | 616.95 | 993.72 |
| United Arab Emirates | 21 | 766.81 | 545.8 | 905.63 |
| Sri Lanka | 20 | 905.98 | 701.02 | 978.66 |
| Kenya | 6 | 781.82 | 715.26 | 897.82 |
| United Kingdom | 2 | 1111.85 | 1049.5 | 1174.21 |

By supplier (top 15 by bill count):

| Supplier | On platform | Bills | Median | P25 | P75 |
| --- | --- | ---: | ---: | ---: | ---: |
| Crystal Agri Foods Impex | True | 48 | 796.19 | 529.48 | 909.02 |
| Modern Foods Impex | True | 47 | 616.37 | 489.78 | 812.91 |
| An Phat Agricultural Products Joint Stock Company | True | 39 | 805.01 | 547.14 | 925.12 |
| SHUBH AGRO PRODUCTS PVT LTD | False | 35 | 682.51 | 496.34 | 824.9 |
| Tanjung Trading Sdn Bhd | True | 28 | 839.6 | 642.91 | 993.72 |
| Gulf Star General Trading LLC | True | 26 | 905.98 | 560.72 | 1014.85 |
| Prime Spices Pvt Ltd | True | 21 | 768.61 | 608.88 | 965.97 |
| Dune Line Foodstuff LLC | True | 21 | 684.35 | 530.36 | 900.5 |
| Nam Viet Seafood Company Limited | True | 20 | 692.33 | 562.31 | 761.36 |
| Maa Balaji Agro Pvt Ltd | True | 19 | 684.37 | 534.63 | 922.97 |
| TRUONG THINH COFFEE COMPANY LIMITED | False | 18 | 704.4 | 527.02 | 872.65 |
| Orient Foods Pvt Ltd | True | 17 | 717.93 | 597.88 | 903.74 |
| HOANG LONG COFFEE JOINT STOCK COMPANY | False | 15 | 766.95 | 722.15 | 885.95 |
| Kingsway Food Distributors Ltd | True | 14 | 834.21 | 568.01 | 1068.35 |
| SAO MAI FOOD COMPANY LIMITED | False | 13 | 734.36 | 528.26 | 904.27 |

Listing prices, converted into the same unit when the dimension matches. These are asking prices, not shipment prices.

| Seller | Title | Listed unit | Min | Max | Min per typical | Max per typical |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Brgiht Commodities Impex | Premium IR64 parboiled rice 5% broken / India Origin | MT | 389.23 | 530.09 | 389.23 | 530.09 |
| Al Sahra Food Distributors LLC | High Quality 1121 basmati rice | MT | 389.13 | 473.07 | 389.13 | 473.07 |
| Gulf Star General Trading LLC | High Quality Jasmine rice - Bulk Supply | MT | 397.96 | 487.2 | 397.96 | 487.2 |
| Al Sahra Food Distributors LLC | Best Price 1121 basmati rice - Bulk Supply | MT | 381.85 | 458.63 | 381.85 | 458.63 |
| Dune Line General Trading LLC | Export Quality Non basmati rice | MT | 387.64 | 562.19 | 387.64 | 562.19 |
| Kijani International Trading Ltd | Export Quality Jasmine rice | MT | 366.58 | 495.63 | 366.58 | 495.63 |
| Al Safa Trading LLC | Wholesale Pusa basmati rice (OEM available) | MT | 371.73 | 517.84 | 371.73 | 517.84 |
| Al Bayan International Trading LLC | Premium IR64 parboiled rice 5% broken / United Arab Emirates Origin | MT | 401.06 | 503.02 | 401.06 | 503.02 |
| Dune Line Foodstuff LLC | Export Quality IR64 parboiled rice 5% broken (OEM available) | MT | 388.35 | 574.92 | 388.35 | 574.92 |
| Al Noor Commodities FZE | Best Price Jasmine rice / United Arab Emirates Origin | MT | 362.34 | 533.85 | 362.34 | 533.85 |
| Tanjung Trading Sdn Bhd | High Quality IR64 parboiled rice 5% broken | MT | 372.34 | 473.27 | 372.34 | 473.27 |
| Al Safa Trading LLC | 1121 basmati rice | MT | 375.77 | 421.78 | 375.77 | 421.78 |
| Al Majd General Trading LLC | 1121 golden sella basmati rice - Bulk Supply | MT | 418.21 | 539.16 | 418.21 | 539.16 |
| Permata International Trading Sdn Bhd | Best Price Non basmati rice for Export | MT | 403.73 | 497.19 | 403.73 | 497.19 |
| Kingsway Food Distributors Ltd | Pusa basmati rice - Bulk Supply | MT | 389.22 | 532.38 | 389.22 | 532.38 |

### Q6

Pandalus borealis cold-water shrimp, frozen

- Product: Pandalus borealis cold-water shrimp, frozen → HS 030616 (Agriculture & Food), quantity None
- Destination: not stated
- Preferred origin: not stated
- Excluded origin: not stated
- Certificates: not stated

43 sellers match the extracted constraints.
Relaxed: nothing. Ranked as of 2026-09-30. 43 sellers in the set, 10 shown.

1. Narmada Food Products Pvt Ltd (ENT-01187, manufacturer)
   Exported HS 030616 26 times.
   Listings: Wholesale Frozen cold water shrimp (030616)
2. Zenith Foods Pvt Ltd (ENT-01372, manufacturer)
   Exported HS 030616 21 times.
   No listing is classified as this code.
3. Deccan Food Products Industries (ENT-01947, manufacturer)
   Exported HS 030616 14 times.
   Listings: High Quality Frozen Pandalus borealis shrimp (030616)
4. Om Umiya Agri Foods Pvt Ltd (ENT-02004, manufacturer)
   Exported HS 030616 11 times.
   No listing is classified as this code.
5. Unique Spices International (ENT-00844, manufacturer)
   Exported HS 030616 7 times.
   Listings: High Quality Frozen cold water shrimp (030616)
6. Redwood Food Distributors LLC (ENT-01080, mixed)
   Exported HS 030616 7 times.
   Listings: Frozen northern prawns - Bulk Supply (030616); Premium Frozen Pandalus borealis shrimp (030616)
7. Bach Dang Coffee Joint Stock Company (ENT-03817, manufacturer)
   Exported HS 030616 9 times.
   Listings: Best Price Frozen cold water shrimp - Bulk Supply (030616)
8. Prairie Group Inc. (ENT-00883, mixed)
   Exported HS 030616 11 times.
   Listings: High Quality Frozen cold water shrimp (030616)
9. Harmoni Trading Sdn Bhd (ENT-02847, mixed)
   Exported HS 030616 5 times.
   Listings: High Quality Frozen Pandalus borealis shrimp | Malaysia Origin (030616)
10. Al Fajr Commodities LLC (ENT-04180, trader)
   Exported HS 030616 8 times.
   Listings: Frozen northern prawns (OEM available) (030616)

### Q7

Radial car tyres 205/55R16, 2 x 40ft containers to Mombasa

- Product: Radial car tyres 205/55R16, 2 x 40ft containers to Mombasa → HS 401110 (Automotive), quantity 2.0
- Destination: Kenya, port Mombasa
- Preferred origin: not stated
- Excluded origin: not stated
- Certificates: not stated

11 sellers match the extracted constraints.
Relaxed: nothing. Ranked as of 2026-09-30. 11 sellers in the set, 10 shown.

1. Shri Lakshmi Automotive Exports (ENT-02996, manufacturer)
   Exported HS 401110 to Kenya 4 times in the 12 months before this request. Discharged at Mombasa on 4 of those bills.
   No listing is classified as this code.
2. Al Noor International LLC (ENT-03510, mixed)
   Exported HS 401110 to Kenya once in the 12 months before this request. Discharged at Mombasa on 1 of those bills.
   Listings: Best Price New car tires (401110); High Quality PCR tyres | United Arab Emirates Origin (401110)
3. Hoang Long Production Joint Stock Company (ENT-03829, manufacturer)
   Exported HS 401110 to Kenya once in the 12 months before this request. Discharged at Mombasa on 1 of those bills.
   Listings: Best Price Radial car tyres 205/55R16 - Bulk Supply (401110); High Quality PCR tyres for Export (401110)
4. Shenzhen Anjia Auto Parts Co., Ltd. (ENT-01785, manufacturer)
   Exported HS 401110 to Kenya once in the 12 months before this request. Discharged at Mombasa on 1 of those bills.
   Listings: High Quality PCR tyres - Bulk Supply (401110); Passenger car tyres for Export (401110)
5. PT Bintang Timur Ban (ENT-00530, manufacturer)
   Exported HS 401110 to Kenya 2 times. Discharged at Mombasa on 2 of those bills.
   Listings: New car tires (401110); New car tires | Indonesia Origin (401110)
6. Shree Siddhivinayak Auto Parts Pvt Ltd (ENT-00292, manufacturer)
   Exported HS 401110 to Kenya 2 times. Discharged at Mombasa on 2 of those bills.
   Listings: PCR tyres (401110); High Quality New car tires (401110)
7. Xiamen Chengfu Tyre Co., Ltd. (ENT-02495, manufacturer)
   Exported HS 401110 to Kenya 2 times. Discharged at Mombasa on 2 of those bills.
   Listings: Passenger car tyres | China Origin (401110)
8. Granite Auto Spares LLC (ENT-02165, mixed)
   Exported HS 401110 to Kenya once. Discharged at Mombasa on 1 of those bills.
   Listings: New car tires - Bulk Supply (401110)
9. Heartland International Trading Inc. (ENT-02023, trader)
   Exported HS 401110 to Kenya once. Discharged at Mombasa on 1 of those bills.
   Listings: Best Price Passenger car tyres (OEM available) (401110); Wholesale Passenger car tyres (OEM available) (401110)
10. Lanka Star Commodities Trading (Pvt) Ltd (ENT-02336, mixed)
   Exported HS 401110 to Kenya once. Discharged at Mombasa on 1 of those bills.
   No listing is classified as this code.

### Q8

Compare prices for refined white sugar ICUMSA 45 across origins

- Product: Compare prices for refined white sugar ICUMSA 45 across origins → HS 170199 (Agriculture & Food), quantity None
- Destination: not stated
- Preferred origin: not stated
- Excluded origin: not stated
- Certificates: not stated

89 sellers match the extracted constraints.
Relaxed: nothing. Ranked as of 2026-09-30. 89 sellers in the set, 10 shown.

1. Crescent Seafoods LLC (ENT-01989, manufacturer)
   Exported HS 170199 49 times.
   Listings: Refined white sugar ICUMSA 45 for Export (170199)
2. Al Hadaf Food Products FZE (ENT-02845, manufacturer)
   Exported HS 170199 33 times.
   Listings: Best Price White crystal sugar S30 | United Arab Emirates Origin (170199); Best Price White crystal sugar S30 (OEM available) (170199)
3. Pearl Coast Food Products FZE (ENT-03972, manufacturer)
   Exported HS 170199 18 times.
   Listings: Wholesale ICUMSA 45 sugar in 50kg bags for Export (170199)
4. BLUE HORIZON SEAFOODS FZE (ENT-01565, manufacturer)
   Exported HS 170199 18 times.
   Listings: High Quality White crystal sugar S30 - Bulk Supply (170199); Wholesale ICUMSA 45 sugar in 50kg bags (170199); Export Quality Refined cane sugar for Export (170199)
5. Al Mutairi Supplies Est. (ENT-00518, mixed)
   Exported HS 170199 14 times.
   Listings: Refined cane sugar - Bulk Supply (170199)
6. Gomes Agropecuária Ltda. (ENT-01781, manufacturer)
   Exported HS 170199 13 times.
   Listings: Best Price White crystal sugar S30 (OEM available) (170199); White crystal sugar S30 (170199)
7. Al Khaleej Food Products LLC (ENT-00066, manufacturer)
   Exported HS 170199 18 times.
   Listings: Best Price Refined white sugar ICUMSA 45 | United Arab Emirates Origin (170199); Export Quality ICUMSA 45 sugar in 50kg bags for Export (170199); Export Quality White crystal sugar S30 - Bulk Supply (170199)
8. Bluewater International Trading LLC (ENT-01117, trader)
   Exported HS 170199 13 times.
   No listing is classified as this code.
9. Horus Food Products S.A.E. (ENT-03994, manufacturer)
   Exported HS 170199 18 times.
   Listings: High Quality White crystal sugar S30 - Bulk Supply (170199)
10. Al Ahram Agro S.A.E. (ENT-01582, manufacturer)
   Exported HS 170199 20 times.
   Listings: Best Price ICUMSA 45 sugar in 50kg bags for Export (170199); ICUMSA 45 sugar in 50kg bags (170199)

Traded unit price for HS 170199 (Cane or beet sugar, refined, other), USD per MT. 659 bills kept, 0 dropped for a different dimension.

By origin:

| Origin | Bills | Median | P25 | P75 |
| --- | ---: | ---: | ---: | ---: |
| United Arab Emirates | 262 | 620.16 | 559.33 | 681.98 |
| Egypt | 144 | 619.72 | 560.69 | 681.05 |
| India | 118 | 627.62 | 572.35 | 682.1 |
| Brazil | 108 | 630.31 | 560.36 | 671.64 |
| United States | 12 | 628.0 | 613.21 | 673.37 |
| Saudi Arabia | 11 | 676.15 | 534.68 | 772.4 |
| United Kingdom | 4 | 582.31 | 540.83 | 623.79 |

By supplier (top 15 by bill count):

| Supplier | On platform | Bills | Median | P25 | P75 |
| --- | --- | ---: | ---: | ---: | ---: |
| Crescent Seafoods LLC | True | 49 | 684.23 | 604.68 | 732.9 |
| Al Hadaf Food Products FZE | True | 33 | 594.17 | 535.63 | 675.17 |
| Al Ahram Agro S.A.E. | True | 19 | 596.82 | 506.1 | 642.46 |
| BLUE HORIZON SEAFOODS FZE | True | 18 | 551.67 | 528.2 | 621.03 |
| Pearl Coast Food Products FZE | True | 18 | 542.69 | 500.38 | 613.89 |
| NILE COMMODITIES S.A.E | False | 17 | 663.56 | 607.24 | 713.43 |
| Horus Food Products S.A.E. | True | 17 | 677.82 | 582.32 | 721.24 |
| Al Khaleej Food Products LLC | True | 17 | 634.44 | 594.52 | 742.6 |
| Pearl Coast Seafoods LLC | False | 15 | 618.54 | 574.91 | 668.65 |
| Al Mutairi Supplies Est. | True | 14 | 608.02 | 505.93 | 640.31 |
| SHRI BHAGWATI AGRI FOODS LLP | False | 14 | 631.3 | 584.51 | 672.07 |
| Gomes Alimentos Ltda. | True | 14 | 632.3 | 615.66 | 674.21 |
| Pearl Coast Agro LLC | True | 13 | 641.54 | 561.23 | 667.99 |
| Gomes Agropecuária Ltda. | True | 13 | 631.09 | 570.14 | 668.45 |
| Bluewater International Trading LLC | True | 13 | 622.26 | 545.15 | 678.55 |

Listing prices, converted into the same unit when the dimension matches. These are asking prices, not shipment prices.

| Seller | Title | Listed unit | Min | Max | Min per typical | Max per typical |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Pearl Coast Food Products FZE | Wholesale ICUMSA 45 sugar in 50kg bags for Export | MT | 510.39 | 735.95 | 510.39 | 735.95 |
| Windsor Provisions Ltd | Premium ICUMSA 45 sugar in 50kg bags for Export | MT | 488.19 | 615.38 | 488.19 | 615.38 |
| Al Rawda International LLC | White crystal sugar S30 | MT | 504.42 | 752.57 | 504.42 | 752.57 |
| Al Hadaf Commodities Trading LLC | Premium White crystal sugar S30 / United Arab Emirates Origin | MT | 522.93 | 688.95 | 522.93 | 688.95 |
| Dune Line General Trading LLC | Wholesale Refined white sugar ICUMSA 45 - Bulk Supply | MT | 470.83 | 549.99 | 470.83 | 549.99 |
| Northstar Wholesale LLC | ICUMSA 45 sugar in 50kg bags for Export | MT | 506.13 | 568.45 | 506.13 | 568.45 |
| Summit International Inc. | High Quality Refined white sugar ICUMSA 45 for Export | MT | 512.48 | 754.03 | 512.48 | 754.03 |
| Oasis Trading LLC | Best Price White crystal sugar S30 - Bulk Supply | MT | 478.93 | 680.77 | 478.93 | 680.77 |
| Windsor Food Distributors Ltd | Refined cane sugar - Bulk Supply | MT | 450.67 | 607.63 | 450.67 | 607.63 |
| Al Harbi General Trading Est. | Refined white sugar ICUMSA 45 (OEM available) | MT | 491.98 | 650.17 | 491.98 | 650.17 |
| Al Harbi General Trading Est. | Premium Refined cane sugar for Export | MT | 459.15 | 678.21 | 459.15 | 678.21 |
| Al Fajr Commodities LLC | Best Price ICUMSA 45 sugar in 50kg bags for Export | MT | 495.36 | 669.06 | 495.36 | 669.06 |
| Pearl Coast Commodities Trading LLC | Premium Refined cane sugar (OEM available) | MT | 513.97 | 650.41 | 513.97 | 650.41 |
| Al Mutairi Supplies Est. | Refined cane sugar - Bulk Supply | MT | 471.16 | 551.2 | 471.16 | 551.2 |
| Al Majd Foodstuff FZE | Export Quality Refined white sugar ICUMSA 45 | MT | 474.38 | 597.75 | 474.38 | 597.75 |

## Posted RFQs

### RFQ-0007

We need two items: 1) packaged black tea 100 g - 17,480 kgs 2) long grain parboiled rice - 140 tons. Both CIF Jebel Ali Port. Prefer India or United Kingdom origin. Prompt shipment.

Buyer excluded: Gulf Star General Trading LLC (ENT-02940). Request date 2026-05-18T15:14:36.

- Product: packaged black tea 100 g → HS 090230 (Agriculture & Food), quantity 17480.0 KG
- Product: long grain parboiled rice → HS 100630 (Agriculture & Food), quantity 140.0 MT
- Destination: United Arab Emirates, port Jebel Ali
- Preferred origin: India, United Kingdom
- Excluded origin: not stated
- Certificates: not stated

41 sellers match the extracted constraints.
Relaxed: nothing. Ranked as of 2026-05-18. 41 sellers in the set, 10 shown.

1. Modern Foods Impex (ENT-03938, manufacturer)
   Exported HS 100630 to United Arab Emirates 20 times in the 12 months before this request. Shipments of this code originated in India.
   Listings: Pusa basmati rice (100630)
2. Prime Spices Pvt Ltd (ENT-01341, manufacturer)
   Exported HS 100630 to United Arab Emirates 11 times in the 12 months before this request. Shipments of this code originated in India. Discharged at Jebel Ali on 1 of those bills.
   Listings: Best Price Long grain white rice - Bulk Supply (100630); High Quality Sona masoori rice | India Origin (100630); Jasmine rice - Bulk Supply (100630)
3. Kingsway Food Distributors Ltd (ENT-01761, trader)
   Exported HS 100630 to United Arab Emirates 6 times in the 12 months before this request. Shipments of this code originated in India and United Kingdom. Discharged at Jebel Ali on 6 of those bills.
   Listings: High Quality Black tea bags (090230); Pusa basmati rice - Bulk Supply (100630)
4. Pragati Agro Pvt Ltd (ENT-02569, manufacturer)
   Exported HS 100630 to United Arab Emirates 5 times in the 12 months before this request. Shipments of this code originated in India. Discharged at Jebel Ali on 4 of those bills.
   Listings: Best Price Long grain white rice for Export (100630); Premium black tea 500g pouch (090230); Long grain white rice (100630)
5. Aravali Food Products Impex (ENT-02868, manufacturer)
   Exported HS 100630 to United Arab Emirates 3 times in the 12 months before this request. Shipments of this code originated in India.
   Listings: IR64 parboiled rice 5% broken - Bulk Supply (100630)
6. Twiga Agro Products Ltd (ENT-00393, manufacturer)
   Exported HS 090230 to United Arab Emirates 5 times in the 12 months before this request. Discharged at Jebel Ali on 4 of those bills.
   Listings: Export Quality Packaged black tea 100 g (090230)
7. Crescent Seafoods (Pvt.) Ltd. (ENT-00498, manufacturer)
   Exported HS 100630 to United Arab Emirates 5 times in the 12 months before this request. Discharged at Jebel Ali on 1 of those bills.
   Listings: High Quality Long grain parboiled rice for Export (100630); Export Quality Non basmati rice (100630); Export Quality Jasmine rice for Export (100630)
8. Sialkot Star Commodities (Pvt.) Ltd. (ENT-01594, manufacturer)
   Exported HS 100630 to United Arab Emirates 5 times in the 12 months before this request. Discharged at Jebel Ali on 3 of those bills.
   Listings: Export Quality Long grain white rice | Pakistan Origin (100630); Export Quality IR64 parboiled rice 5% broken (OEM available) (100630)
9. Nyati Provisions Ltd (ENT-01217, mixed)
   Exported HS 100630 to United Arab Emirates 3 times in the 12 months before this request. Shipments of this code originated in India. Discharged at Jebel Ali on 3 of those bills.
   Listings: Long grain parboiled rice - Bulk Supply (100630); Jasmine rice (OEM available) (100630)
10. Tanjung Trading Sdn Bhd (ENT-03293, trader)
   Exported HS 100630 to United Arab Emirates 4 times in the 12 months before this request.
   Listings: High Quality IR64 parboiled rice 5% broken (100630)

### RFQ-0027

Hello, our company imports halal frozen boneless beef into Malaysia. We need 420 metric tons. One-time order. CIF Pasir Gudang. Prefer Brazil or India origin. Suppliers with export experience to Malaysia preferred.

Buyer excluded: Seri Maju Trading Sdn Bhd (ENT-02463). Request date 2026-09-10T01:55:43.

- Product: halal frozen boneless beef → HS 020230 (Agriculture & Food), quantity 420.0 MT
- Destination: Malaysia, port Pasir Gudang
- Preferred origin: Brazil, India
- Excluded origin: not stated
- Certificates: HALAL

4 sellers match the extracted constraints.
Relaxed: nothing. Ranked as of 2026-09-10. 4 sellers in the set, 4 shown.

1. Omkar Food Products LLP (ENT-00792, manufacturer)
   Exported HS 020230 to Malaysia 2 times in the 12 months before this request. Shipments of this code originated in India. Discharged at Pasir Gudang on 2 of those bills. Holds Halal.
   Listings: Best Price Frozen buffalo meat topside | India Origin (020230)
2. Costa Agropecuária Ltda. (ENT-00808, manufacturer)
   Exported HS 020230 to Malaysia 2 times in the 12 months before this request. Shipments of this code originated in Brazil. Holds Halal.
   Listings: High Quality Halal frozen boneless beef | Brazil Origin (020230)
3. Navkar Commodities Enterprises (ENT-01544, manufacturer)
   Exported HS 020230 to Malaysia once in the 12 months before this request. Shipments of this code originated in India. Discharged at Pasir Gudang on 1 of those bills. Holds Halal.
   Listings: High Quality Frozen boneless buffalo meat - Bulk Supply (020230)
4. Shri Annapurna Agro Products Pvt Ltd (ENT-02915, manufacturer)
   Exported HS 020230 to Malaysia 3 times. Shipments of this code originated in India. Holds Halal.
   Listings: Best Price Frozen buffalo meat topside (020230); Frozen boneless buffalo meat (020230)

### RFQ-0052

Requirement: grey portland cement
Qty - 9,140 metric tons
Port - BDCGP
Terms - DAP
Certs - ISO 14001 certification required.
Origin - Prefer Egypt or Turkey origin. United Arab Emirates origin not acceptable.
Shipment: Need by October 2026.

Buyer excluded: Rahman Group Ltd. (ENT-01405). Request date 2026-09-02T21:56:58.

- Product: grey portland cement → HS 252329 (Construction Materials), quantity 9140.0 MT
- Destination: Bangladesh, port Chattogram
- Preferred origin: Egypt, Turkey
- Excluded origin: United Arab Emirates
- Certificates: ISO_14001

3 sellers match the extracted constraints.
Relaxed: nothing. Ranked as of 2026-09-02. 3 sellers in the set, 3 shown.

1. Arslan Çimento San. ve Tic. A.Ş. (ENT-02757, manufacturer)
   Exported HS 252329 to Bangladesh 7 times in the 12 months before this request. Shipments of this code originated in Turkey. Discharged at Chattogram on 7 of those bills. Holds ISO 14001.
   Listings: Wholesale OPC 42.5 cement for Export (252329)
2. Demir Çimento San. ve Tic. Ltd. Şti. (ENT-02816, manufacturer)
   Exported HS 252329 to Bangladesh 2 times in the 12 months before this request. Shipments of this code originated in Turkey. Discharged at Chattogram on 1 of those bills. Holds ISO 14001.
   Listings: Wholesale OPC 42.5 cement for Export (252329); OPC 42.5 cement - Bulk Supply (252329); Wholesale Ordinary portland cement OPC 53 - Bulk Supply (252329)
3. Kılıç Seramik San. ve Tic. Ltd. Şti. (ENT-03800, manufacturer)
   Exported HS 252329 to Bangladesh 2 times in the 12 months before this request. Shipments of this code originated in Turkey. Holds ISO 14001.
   Listings: High Quality OPC 42.5 cement for Export (252329)

### RFQ-0257

dear supplier, kindly provide price for passenger car tyres qty 4530 pcs delivery ZADUR (CFR). Only TS 16949/IATF certified suppliers. thanks

Buyer excluded: Cape Point Trading (Pty) Ltd (ENT-00520). Request date 2026-01-07T06:43:21.

- Product: passenger car tyres → HS 401110 (Automotive), quantity 4530.0 PCS
- Destination: South Africa, port Durban
- Preferred origin: not stated
- Excluded origin: not stated
- Certificates: IATF_16949

5 sellers match the extracted constraints.
Relaxed: nothing. Ranked as of 2026-01-07. 5 sellers in the set, 5 shown.

1. Al Rawda International Trading LLC (ENT-03751, trader)
   Exported HS 401110 to South Africa 3 times in the 12 months before this request. Discharged at Durban on 3 of those bills. Holds IATF 16949.
   Listings: Radial car tyres 205/55R16 (OEM available) (401110)
2. PT Mitra Usaha Ban (ENT-03942, manufacturer)
   Exported HS 401110 to South Africa 2 times in the 12 months before this request. Discharged at Durban on 1 of those bills. Holds IATF 16949.
   Listings: Radial car tyres 205/55R16 (401110)
3. Yiwu Henghai Tyre Co., Ltd. (ENT-02445, manufacturer)
   Exported HS 401110 to South Africa once in the 12 months before this request. Discharged at Durban on 1 of those bills. Holds IATF 16949.
   Listings: PCR tyres - Bulk Supply (401110); New car tires for Export (401110)
4. Al Shehri Tyres Co. (ENT-03536, mixed)
   Exported HS 401110 to South Africa once. Discharged at Durban on 1 of those bills. Holds IATF 16949.
   Listings: Premium PCR tyres (OEM available) (401110); Wholesale Passenger car tyres | Saudi Arabia Origin (401110)
5. Guangzhou Taiyuan Brake System Co., Ltd. (ENT-01385, manufacturer)
   Exported HS 401110 to South Africa once. Discharged at Durban on 1 of those bills. Holds IATF 16949.
   Listings: Premium Radial car tyres 205/55R16 (401110)

### RFQ-0399

Urgent!! disc brake rotors required, 47,690 kgs, CIF El Dekheila.

Buyer excluded: Al Nasr International S.A.E. (ENT-03799). Request date 2026-04-17T09:11:01.

- Product: disc brake rotors → HS 870830 (Automotive), quantity 47690.0 KG
- Destination: Egypt, port El Dekheila
- Preferred origin: not stated
- Excluded origin: not stated
- Certificates: not stated

9 sellers match the extracted constraints.
Relaxed: nothing. Ranked as of 2026-04-17. 9 sellers in the set, 9 shown.

1. Tianjin Yishun Auto Parts Co., Ltd. (ENT-00344, manufacturer)
   Exported HS 870830 to Egypt 6 times in the 12 months before this request. Discharged at El Dekheila on 1 of those bills.
   Listings: Brake calipers | China Origin (870830)
2. YIWU LONGJIA AUTO PARTS CO., LTD. (ENT-02853, manufacturer)
   Exported HS 870830 to Egypt 2 times in the 12 months before this request.
   Listings: Export Quality Brake discs (870830)
3. Deccan Auto Components International (ENT-04178, manufacturer)
   Exported HS 870830 to Egypt 2 times in the 12 months before this request.
   Listings: Wholesale Brake discs | India Origin (870830)
4. Al Noor Commodities Trading LLC (ENT-03485, mixed)
   Exported HS 870830 to Egypt once in the 12 months before this request.
   Listings: Brake calipers (870830)
5. Bintang Imports Sdn Bhd (ENT-00273, mixed)
   Exported HS 870830 to Egypt once in the 12 months before this request.
   Listings: High Quality Brake calipers - Bulk Supply (870830); High Quality Disc brake rotors - Bulk Supply (870830)
6. Tianjin Tianfeng Auto Parts Co., Ltd. (ENT-03119, manufacturer)
   Exported HS 870830 to Egypt 2 times.
   Listings: Wholesale Brake pads (870830); Wholesale Brake calipers (870830)
7. Guangzhou Bosheng Brake System Co., Ltd. (ENT-02848, manufacturer)
   Exported HS 870830 to Egypt once.
   Listings: Wholesale Brake pads - Bulk Supply (870830)
8. Jai Balaji Auto Parts Impex Pvt Ltd (ENT-02953, manufacturer)
   Exported HS 870830 to Egypt once. Discharged at El Dekheila on 1 of those bills.
   Listings: Premium Brake pads - Bulk Supply (870830)
9. Malabar Auto Parts Exim Pvt Ltd (ENT-01984, manufacturer)
   Exported HS 870830 to Egypt once. Discharged at El Dekheila on 1 of those bills.
   Listings: Brake discs (870830)

## Scorecards

### CMP-04013 — Shenzhen Yijia Steel Co., Ltd.

ENT-03474. Activity manufacturer. Roles: manufacturer, exporter. On platform: True. Year established: 1999.
Export bills 25 from 2024-11-15 to 2026-08-23. Valued company-buyer bills 25, $29,616,246. Import bills 0, $0.

Risk flags:

- Customer concentration: Al Dossary Wholesale Est. is 98% of export value (22 bills, $28,964,633 of $29,616,246).
- Trading versus manufacturing: manufacturer.

Registrations:

| Id | Name | City | Country | Declared type | Link method |
| --- | --- | --- | --- | --- | --- |
| CMP-04013 | Shenzhen Yijia Steel Co., Ltd. | Shenzhen | China | Manufacturer and Exporter | singleton |

Certifications:

- None.

Export destinations:

- Saudi Arabia: 24 bills
- United Arab Emirates: 1 bills

Export origins:

- China: 25 bills

Buyers by export value:

- Al Dossary Wholesale Est.: 22 bills, $28,964,633
- AL HARBI WHOLESALE EST: 2 bills, $336,417
- DUNE LINE INTERNATIONAL TRADING LLC: 1 bills, $315,195

HS codes shipped:

- 720839: 16 bills
- 730640: 3 bills
- No HS code: 6 bills

Import origins:


Bought from:


Platform responsiveness. Chat accept rate is chats this company accepted divided by chat requests directed at it. Quotation accept rate is quotations accepted by the counterparty divided by quotations this company sent. RFQ responses are responses this company performed.

- Chat requests received: 2. Accepted: 1. Rate: 0.5.
- Quotations sent: 0. Accepted: 0. Rate: not applicable.
- RFQ responses: 1.

### CMP-00260 — MAA KHODIYAR DIAMONDS INDUSTRIES (P) LTD

ENT-00260. Activity manufacturer. Roles: manufacturer, exporter. On platform: True. Year established: 1976.
Export bills 11 from 2025-02-07 to 2026-07-05. Valued company-buyer bills 11, $24,613,774. Import bills 0, $0.

Risk flags:

- Customer concentration: largest buyer Gulf Star Trading FZE is 34% of export value. The 60% line is not crossed.
- Trading versus manufacturing: manufacturer.

Registrations:

| Id | Name | City | Country | Declared type | Link method |
| --- | --- | --- | --- | --- | --- |
| CMP-00260 | Maa Khodiyar Diamonds Industries Pvt Ltd | New Delhi | India | Manufacturer & Exporter | phone |
| CMP-02827 | MAA KHODIYAR DIAMONDS INDUSTRIES (P) LTD | New Delhi | India | Supplier | phone |

Certifications:

- None.

Export destinations:

- United Arab Emirates: 6 bills
- United Kingdom: 3 bills
- Italy: 2 bills

Export origins:

- India: 11 bills

Buyers by export value:

- Gulf Star Trading FZE: 4 bills, $8,390,741
- Al Shams Distributors LLC: 2 bills, $7,599,379
- Mercia Supplies Ltd: 1 bills, $4,664,486
- WINDSOR GEMS LTD: 2 bills, $2,343,215
- ROSSI GIOIELLI DISTRIBUZIONE SRL: 2 bills, $1,615,953

HS codes shipped:

- 710239: 9 bills
- No HS code: 2 bills

Import origins:


Bought from:


Platform responsiveness. Chat accept rate is chats this company accepted divided by chat requests directed at it. Quotation accept rate is quotations accepted by the counterparty divided by quotations this company sent. RFQ responses are responses this company performed.

- Chat requests received: 1. Accepted: 0. Rate: 0.0.
- Quotations sent: 0. Accepted: 0. Rate: not applicable.
- RFQ responses: 1.

### CMP-04471 — Langkawi Trading Sdn Bhd

ENT-03803. Activity trader. Roles: trader. On platform: True. Year established: 2003.
Export bills 8 from 2025-05-31 to 2026-09-22. Valued company-buyer bills 8, $6,813,286. Import bills 5, $1,169,655.

Risk flags:

- Customer concentration: largest buyer Misr Star Provisions for Import & Export is 42% of export value. The 60% line is not crossed.
- Trading versus manufacturing: trader. No manufacturing signal on the registrations or the listings.

Registrations:

| Id | Name | City | Country | Declared type | Link method |
| --- | --- | --- | --- | --- | --- |
| CMP-04471 | Langkawi Trading Sdn Bhd | Shah Alam | Malaysia | Trading Company | singleton |

Certifications:

- KOSHER (Kosher), raw text `Kosher`

Export destinations:

- United States: 5 bills
- India: 2 bills
- Egypt: 1 bills

Export origins:

- Malaysia: 4 bills
- Brazil: 2 bills
- Vietnam: 2 bills

Buyers by export value:

- Misr Star Provisions for Import & Export: 1 bills, $2,881,777
- SHREE GAYATRI IMPORTS PVT LTD: 2 bills, $1,944,884
- Northstar Provisions Inc.: 3 bills, $1,339,021
- Prairie Commodities Trading Inc.: 1 bills, $368,745
- Union Foods L.L.C: 1 bills, $278,858

HS codes shipped:

- 090411: 4 bills
- 080131: 3 bills
- No HS code: 1 bills

Import origins:

- Brazil: 2 bills
- Vietnam: 2 bills
- Indonesia: 1 bills

Bought from:

- ALMEIDA CARNES LTDA: 2 bills
- Tan Thanh Food Company Limited: 2 bills
- PRAIRIE COMMODITIES TRADING CORP: 1 bills

Platform responsiveness. Chat accept rate is chats this company accepted divided by chat requests directed at it. Quotation accept rate is quotations accepted by the counterparty divided by quotations this company sent. RFQ responses are responses this company performed.

- Chat requests received: 5. Accepted: 4. Rate: 0.8.
- Quotations sent: 2. Accepted: 0. Rate: 0.0.
- RFQ responses: 0.

