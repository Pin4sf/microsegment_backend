import { register } from "@shopify/web-pixels-extension";

register(({ analytics, browser, init, settings }) => {
  const fastapi_endpoint =
    "https://alien-adapted-gecko.ngrok-free.app/api/data/shopify/event";
  const create_event_entry = async (event_name, payload, shop, account_id) => {
    const data = {
      event_name: event_name,
      payload: payload,
      shop: shop,
      account_id: account_id,
    };
    const response = await fetch(fastapi_endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
      keepalive: true,
    });
    const d = await response.json();
    console.log(d);
  };

  // When user visits any page
  analytics.subscribe("page_viewed", async (event) => {
    console.log("Page viewed", event);
    console.log("Customer", init.data.customer);

    const payload = {
      customer: init.data.customer,
    };

    create_event_entry(event.name, payload, init.data.shop, settings.accountID);
  });

  // When user opens any product page
  analytics.subscribe("product_viewed", (event) => {
    console.log("Product viewed", event.data.productVariant.product.title);
    payload = {
      customer: init.data.customer,
      data: event.data.productVariant,
    };
    create_event_entry(event.name, payload, init.data.shop, settings.accountID);
  });

  // When user submits any search query
  analytics.subscribe("search_submitted", (event) => {
    payload = {
      customer: init.data.customer,
      data: event.data.searchResult,
    };
    create_event_entry(event.name, payload, init.data.shop, settings.accountID);
  });

  // When user visits their cart page
  analytics.subscribe("cart_viewed", (event) => {
    const cart = event.data.cart;
    console.log("Cart viewed", cart);
    payload = {
      customer: init.data.customer,
      data: event.data.cart,
    };
    create_event_entry(event.name, payload, init.data.shop, settings.accountID);
  });

  // When user successfully completes a checkout
  analytics.subscribe("checkout_completed", (event) => {
    const checkout = event.data.checkout;
    const checkoutTotalPrice = checkout.totalPrice?.amount;

    const allDiscountCodes = checkout.discountApplications.map((discount) => {
      if (discount.type === "DISCOUNT_CODE") {
        return discount.title;
      }
    });

    console.log("Checkout Completed", checkout);
    console.log("Total Amount", checkoutTotalPrice);
    console.log("Discount Codes used", allDiscountCodes);
    payload = {
      customer: init.data.customer,
      data: event.data.checkout,
    };
    create_event_entry(event.name, payload, init.data.shop, settings.accountID);
  });

  // When user visits a collection
  analytics.subscribe("collection_viewed", (event) => {
    const collection = event.data.collection;
    const collectionTitle = collection.title;
    console.log("Collection Viewed", collectionTitle);
    payload = {
      customer: init.data.customer,
      data: event.data.collection,
    };
    create_event_entry(event.name, payload, init.data.shop, settings.accountID);
  });

  // When user adds a product into their cart
  analytics.subscribe("product_added_to_cart", (event) => {
    const cartLine = event.data.cartLine;
    const cartLineCost = cartLine.cost.totalAmount.amount;
    const ProductTitle = cartLine.merchandise.product.title;

    console.log("Product added to cart ", ProductTitle);
    console.log("Total cost of cart", cartLineCost);
    console.log("cartLine", cartLine);
    payload = {
      customer: init.data.customer,
      data: event.data.cartLine,
    };
    create_event_entry(event.name, payload, init.data.shop, settings.accountID);
  });
});
