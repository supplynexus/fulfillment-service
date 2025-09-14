import { frontendApi } from './api';
import { frontendLogger } from './frontend-logger';

// Printify API Types
export interface PrintifyOrderRequest {
  order_id: number;
  customer_name: string;
  customer_email: string;
  address_line1: string;
  city: string;
  state: string;
  country: string;
  zip_code: string;
  phone?: string;
  quantity: number;
}

export interface PrintifyOrderResponse {
  success: boolean;
  printify_order_id?: string;
  external_id?: string;
  status?: string;
  total_price?: number;
  message: string;
}

// Printify API Client
export const printifyApi = {
  /**
   * Create a Printify order
   */
  createOrder: async (request: PrintifyOrderRequest): Promise<PrintifyOrderResponse> => {
    try {
      frontendLogger.info('🚀 开始创建Printify订单', { 
        orderId: request.order_id,
        testMode: request.test_mode 
      });

      const response = await frontendApi.post('/api/printify/orders', request);
      
      frontendLogger.info('✅ Printify订单创建成功', { 
        success: response.data.success,
        printifyOrderId: response.data.printify_order_id 
      });

      return response.data;
    } catch (error: any) {
      frontendLogger.error('❌ Printify订单创建失败', { 
        error: error.message,
        status: error.response?.status,
        data: error.response?.data 
      });
      
      // 如果是API错误，返回错误响应
      if (error.response?.data) {
        return error.response.data;
      }
      
      // 如果是网络错误或其他错误，返回通用错误响应
      throw error;
    }
  },

  /**
   * Get Printify products (for testing)
   */
  getProducts: async (): Promise<any> => {
    try {
      frontendLogger.info('🔍 获取Printify商品列表');

      const response = await frontendApi.get('/api/printify/products');
      
      frontendLogger.info('✅ Printify商品列表获取成功', { 
        count: response.data.products?.length || 0 
      });

      return response.data;
    } catch (error: any) {
      frontendLogger.error('❌ 获取Printify商品列表失败', { 
        error: error.message,
        status: error.response?.status 
      });
      
      throw error;
    }
  }
};
