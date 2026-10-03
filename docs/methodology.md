# Emissions methodology

Version: `epa-2022-inr-reference-v2`. Source retrieval: 1 October 2026.

## Formula

The brief requires price times category multiplier. This implementation uses:

`reference kg CO2e per INR = EPA kg CO2e per 2022 USD / 78.6044905829916`

`estimated kg CO2e = INR purchase price × reference category factor`

Prices and results use Decimal half-up rounding to two decimal places. Factors retain twelve decimal places. The historical conversion is the World Bank indicator PA.NUS.FCRF for India, 2022. It is not a current foreign-exchange quote. Purchase records save methodology version and EPA category code.

The EPA source column is Supply Chain Emission Factors with Margins. The source unit is kg CO2e/2022 USD, purchaser price. The archived selected rows, original values, download URL and full-source SHA-256 are in `data/emission_sources.json`.

## Category mappings and limitations

Apparel maps to NAICS 315990; footwear to 316210; electronics to electronic-computer manufacturing 334111; household goods to plastics-bottle manufacturing 326160; repair to personal/household goods repair 811490. These broad mappings are screening proxies and do not fit every item within the user-facing category. Each category displays its mapping limitation.

New and second-hand clothing share an apparel factor. New and refurbished electronics share a computer factor. Single-use and reusable household goods share a plastics-bottle factor. The model does not assign unsupported discounts to reuse, refurbishment or repeated use. Price differences therefore drive differences for these pairs; they must not be described as measured emissions avoided.

The source represents US economic sectors. A historical exchange-rate conversion does not make it India-specific. Current prices are not inflation-adjusted to the dataset's 2022 price basis. Results are rough reference estimates rather than validated carbon accounting, product lifecycle measurements or proof of a brand's ethical performance. Use supplier-specific lifecycle data for precise decisions.

Free goods return zero under this spend formula, not zero physical emissions. Badges depend on what a person logs and are not audited. Future-dated entries represent planned purchases and appear in the selected future month.

## Badge rules

- Eco Saver: at least three monthly purchases and estimated total at most 50 kg CO2e.
- Low Impact Shopper: at least three reuse, repair or reusable choices and at least 60 percent of recorded monthly purchases. This rewards habits rather than a verified carbon reduction.
- Repair Champion: at least one repair-service entry in the month.
- Turtle leaf: at least one reuse, repair or reusable entry in the selected month.

Empty histories earn no badges. The catalog's internal `lower_impact` flag identifies habit categories, not a measured lower factor. Source factors and fixed badge thresholds are independent of user goals.

## Compatibility

Old `illustrative-inr-v1` JSON backups require an explicit migration opt-in. Import recomputes estimates with current sourced factors and validates IDs, dates, prices, categories, version and currency before any database write. Existing source files were not overwritten or deleted. Source changes require a methodology version change and an explicit migration policy.

## Sources

- https://catalog.data.gov/dataset/supply-chain-greenhouse-gas-emission-factors-v1-3-by-naics-6
- https://pasteur.epa.gov/uploads/10.23719/1531143/SupplyChainGHGEmissionFactors_v1.3.0_NAICS_CO2e_USD2022.csv
- https://api.worldbank.org/v2/country/IND/indicator/PA.NUS.FCRF?date=2022&format=json
