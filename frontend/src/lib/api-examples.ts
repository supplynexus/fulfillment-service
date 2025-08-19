/**
 * API 使用示例
 * 展示如何使用新的认证 API 客户端
 */

import { apiClient } from './auth';

// 示例 1: 获取用户信息
export async function getUserProfile() {
  try {
    const user = await apiClient.get('/api/v1/users/me');
    return user;
  } catch (error) {
    console.error('Failed to get user profile:', error);
    throw error;
  }
}

// 示例 2: 获取订单列表
export async function getOrders() {
  try {
    const orders = await apiClient.get('/api/v1/orders');
    return orders;
  } catch (error) {
    console.error('Failed to get orders:', error);
    throw error;
  }
}

// 示例 3: 创建新订单
export async function createOrder(orderData: any) {
  try {
    const order = await apiClient.post('/api/v1/orders', orderData);
    return order;
  } catch (error) {
    console.error('Failed to create order:', error);
    throw error;
  }
}

// 示例 4: 更新订单
export async function updateOrder(orderId: string, orderData: any) {
  try {
    const order = await apiClient.put(`/api/v1/orders/${orderId}`, orderData);
    return order;
  } catch (error) {
    console.error('Failed to update order:', error);
    throw error;
  }
}

// 示例 5: 删除订单
export async function deleteOrder(orderId: string) {
  try {
    await apiClient.delete(`/api/v1/orders/${orderId}`);
  } catch (error) {
    console.error('Failed to delete order:', error);
    throw error;
  }
}

// 示例 6: 获取客户列表
export async function getCustomers() {
  try {
    const customers = await apiClient.get('/api/v1/customers');
    return customers;
  } catch (error) {
    console.error('Failed to get customers:', error);
    throw error;
  }
}

// 示例 7: 获取产品列表
export async function getProducts() {
  try {
    const products = await apiClient.get('/api/v1/products');
    return products;
  } catch (error) {
    console.error('Failed to get products:', error);
    throw error;
  }
}

// 示例 8: 自定义请求（带额外头部）
export async function customRequest() {
  try {
    const response = await apiClient.request('/api/v1/custom-endpoint', {
      method: 'POST',
      headers: {
        'X-Custom-Header': 'custom-value',
      },
      body: JSON.stringify({ custom: 'data' }),
    });
    return response;
  } catch (error) {
    console.error('Failed to make custom request:', error);
    throw error;
  }
}
