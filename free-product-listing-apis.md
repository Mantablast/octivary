# Free product listing APIs

Notes:
- "Free" below means either fully open/no key, or free to apply for an API key with typical rate limits. Always review terms and limits before production use.
- Marketplace APIs often require a seller account and approval.

## Open or demo product listing APIs (no key)
- Fake Store API (demo e-commerce data)
  - Base: https://fakestoreapi.com
  - Example: https://fakestoreapi.com/products
- DummyJSON (fake REST data including products)
  - Base: https://dummyjson.com
  - Example: https://dummyjson.com/products
- Platzi Fake Store API (EscuelaJS) (products, categories, users)
  - Example: https://api.escuelajs.co/api/v1/products
- Free E-commerce Products API (static JSON dataset)
  - JSON: https://raw.githubusercontent.com/Kolzsticks/Free-Ecommerce-Products-Api/main/main/products.json

## Open product databases (real products)
- Open Food Facts (food product database)
  - Example: https://world.openfoodfacts.org/api/v2/product/737628064502

## Marketplace/retailer product catalogs (free to apply, key/OAuth required)
- Steam Web API (official supported API; listings only)
  - Docs: https://developer.valvesoftware.com/wiki/Steam_Web_API
  - Key: https://steamcommunity.com/dev/apikey
  - Listings: https://api.steampowered.com/ISteamApps/GetAppList/v2/
  - Note: official API does not provide store details like pricing, media, genres/tags, ratings, or publishers. Those require Steamworks partner APIs or the (undocumented) Steam Store endpoints.
- Best Buy API (products, categories)
  - https://bestbuyapis.github.io/api-documentation/#overview
  - Auth: API key
- eBay Developers Program (buy/sell listings)
  - https://developer.ebay.com/
  - Auth: OAuth
- Etsy Open API v3 (shop listings)
  - https://www.etsy.com/developers/documentation/getting_started/api_basics
  - Auth: OAuth
- WooCommerce REST API (your WooCommerce store products)
  - https://woocommerce.github.io/woocommerce-rest-api-docs/
  - Auth: consumer key/secret
- Flipkart Marketplace (seller product listing management)
  - https://seller.flipkart.com/api-docs/FMSAPI.html
  - Auth: OAuth
- Lazada Open API (seller products/metrics)
  - https://open.lazada.com/doc/doc.htm
  - Auth: API key
- MercadoLibre Developers (products, listings)
  - https://developers.mercadolibre.com/
  - Auth: API key/OAuth (varies by endpoint)
- Shopee Open API (seller integrations)
  - https://open.shopee.com/documents?version=1
  - Auth: API key
- Tokopedia Open API (seller integrations)
  - https://developer.tokopedia.com/openapi/guide/#/
  - Auth: OAuth
- Digi-Key API (electronic components catalog)
  - https://www.digikey.com/en/resources/api-solutions
  - Auth: OAuth
- Octopart API (electronic parts data)
  - https://octopart.com/api/v4/reference
  - Auth: API key
- OLX Poland API (classified listings)
  - https://developer.olx.pl/api/doc#section/
  - Auth: API key

## Directories for more options
- Public APIs list (Shopping section)
  - https://github.com/public-apis/public-apis#shopping
- PublicAPIs.dev Shopping category
  - https://publicapis.dev/category/shopping


Looks promising https://gamebrain.co/api/console