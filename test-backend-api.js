// 直接测试后端 API
const testBackendAPI = async () => {
  try {
    console.log('🧪 开始测试后端 API...');
    
    // 模拟订单数据
    const orderData = {
      shopify_order_id: "gid://shopify/Order/5839241838692",
      name: "#1021",
      confirmation_number: "#1021",
      financial_status: "paid",
      fulfillment_status: "unfulfilled",
      confirmed: true,
      closed: false,
      cancelled: false,
      currency_code: "USD",
      total_price: 41.17,
      subtotal_price: 41.17,
      total_tax: 0,
      total_shipping: 0,
      tags: [],
      note: "测试订单",
      customer_data: {
        id: "gid://shopify/Customer/1234567890",
        name: "Test Customer",
        email: "test@example.com",
        phone: "+17804277362"
      },
      billing_address: {
        firstName: "Test",
        lastName: "Customer",
        address1: "10800 97 Avenue Northwest",
        city: "Edmonton",
        province: "Alberta",
        country: "Canada",
        zip: "T5K 2B6"
      },
      shipping_address: {
        firstName: "Test",
        lastName: "Customer",
        address1: "10800 97 Avenue Northwest",
        city: "Edmonton",
        province: "Alberta",
        country: "Canada",
        zip: "T5K 2B6"
      },
      line_items: [
        {
          id: "gid://shopify/LineItem/1234567890",
          title: "Unisex Oversized Boxy Tee",
          quantity: 1,
          price: "41.17",
          variant: {
            title: "White / S"
          }
        }
      ],
      fulfillments: [],
      refunds: [],
      raw_data: {
        id: "gid://shopify/Order/5839241838692",
        name: "#1021",
        createdAt: "2025-09-27T19:54:39Z"
      }
    };
    
    console.log('📤 发送请求到后端 API...');
    
    // 直接调用后端 API（需要认证头）
    const response = await fetch('http://localhost:8000/api/v1/shopify-orders/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-Name': 'test-tenant',
        'X-User-ID': 'test-user',
        'X-Timestamp': Math.floor(Date.now() / 1000).toString(),
        'X-Nonce': 'test-nonce',
        'X-Signature': 'test-signature'
      },
      body: JSON.stringify(orderData)
    });
    
    console.log('📥 收到响应:', response.status, response.statusText);
    
    if (response.ok) {
      const data = await response.json();
      console.log('✅ 订单保存成功！');
      console.log('📊 响应数据:', JSON.stringify(data, null, 2));
    } else {
      const error = await response.text();
      console.log('❌ 保存失败');
      console.log('📊 错误信息:', error);
    }
    
  } catch (error) {
    console.error('💥 测试失败:', error.message);
  }
};

// 运行测试
testBackendAPI();
