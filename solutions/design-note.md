# Design note

The graph that is loaded today is about 95,000 nodes: 8,432 companies, 5,020 registrations, 5,399 products, 50,173 shipments, 26,041 interactions, and 500 requests, plus the small country, port, unit, certificate, and HS vocabularies. Fifty million nodes is a larger version of the same shape. Most of the new nodes would be shipments and interactions. The rules below are what has to stay true when that happens, and when a new file arrives every day.

## Scale and the daily load

Reads already start at a key. A scorecard starts at one registration, walks to its company, and then to that company's shipments. A price comparison starts at one HS code. Those lookups use the uniqueness constraints. They do not scan the graph. The price query is written that way on purpose: `MATCH (h:HSCode {hs_code})` and then the shipments classified as that code.

The part that does not survive 50 million nodes is the search index. The assistant loads every on-platform shipment into memory, because this extract is a few tens of thousands of bills and the load takes about a second. At 50 million shipments that index is the wrong shape. The ranker would start from the sought HS code and the requested destination, collect the companies on those bills, and score that candidate set. The score itself does not change: recent bills on the lane, certificates, a listing of the code. Only the way the candidates are found changes.

The daily load is a merge, not a reload. A new shipment is `MERGE`d on `shipment_id`. A bill of lading that already exists keeps the row with the lower `shipment_id`, which is the same rule the loader uses now, and the bill-of-lading index makes that check local. A new interaction is appended. A new product is classified by the phrase table, which is a fixed list of rules and does not grow with the graph. Rows are still written with `UNWIND` in batches.

There are no summary edges. Customer concentration, responsiveness, and the price bands are computed from the shipments and the interactions when the page is opened. A stored total would have to be updated for every late correction, and the ontology already forbids that kind of edge. At 50 million nodes the computation stays cheap because it is scoped to one company or one HS code, not to the whole graph.

## Entity resolution as new rows arrive

A new registration is not compared with every company. It is compared with the block that shares its phone (last 8 digits), its corporate email domain, or its normalized name and city. Those are the same keys the batch resolver uses. Free inboxes stay ignored. A blank founding year still cannot bridge two dated companies. An undated row joins a block only when the dated rows in that block were founded within a year of each other.

Existing `entity_id` values stay put. A new registration that joins a company gets a `HAS_REGISTRATION` edge and the company keeps its id, so old shipment links do not have to be rewritten. If two companies should become one, the survivor is the lower `entity_id` and the relationships are moved once. Ids are not renumbered on every load.

Off-platform parties stay off-platform until the same linker that runs today would attach them. That linker is exact normalized name plus country, or a typo with a clear gap to the next candidate. A new platform registration does not pull in every similar off-platform name. A same-length substitution (`Hengcheng` / `Fengcheng`) is still rejected. A one-token name such as `HARBOR` still matches too many companies and stays unlinked.

`er_labels.csv` is a regression set. It is not a list of keys the resolver is allowed to memorize. After a rule change, precision and recall on those 200 pairs have to hold before the new clusters are accepted. A new labelled pair that the rules get wrong is a reason to change the rule, not a reason to hard-code the pair.

## What to build next

The next piece is a prospective check of the ranking. The current hit@10 of 0.658 is measured against who replied to the request. A reply is not a fulfilled shipment. The check worth having is: freeze the graph on the day before the request, rank sellers, then see who actually shipped that HS code to that country afterward. A small hand-labelled set would give an NDCG@10 beside it. Until that exists, the reply metric is only a way to notice that a scoring change moved the list.

The second piece is the incremental loader described above, so a daily file does not rewrite 50 million nodes. The third is optional wording. A model could be given the JSON the page already shows and asked to phrase it. It would not be asked to name a supplier, a price, or a certificate, because those are already on the JSON or they are not known.

## What was skipped

Image search was skipped. The pack has no product photos tied to `product_id`. A photo match would still have to return a product that is already in the graph. Without that image catalogue, a vision model would be guessing a title and the guardrail would be the same phrase table we already run on text.

No language model is in the request path. The sentences on the page are filled from the counts the graph returned. Cost per query is $0. Adding a model to invent a supplier would break the rule that every name on the screen is a node.

A request pasted into the page is ranked in memory and is not written back as a new RFQ. The five test requests already exist. Writing demo text into the graph would mix it with the 500 source requests.

Prices convert inside one dimension. Kilograms, metric tons, and grams convert by factors of 1,000. Pieces are not turned into kilograms, and carats are not turned into kilograms. A bill in another dimension is dropped and the drop is counted. Listing prices stay in their own table, next to the traded prices, and are labelled as asking prices.

Summary edges were not added. The ontology says the scorecard reads the same shipments and interactions as every other query.
