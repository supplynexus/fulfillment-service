/**
 * 数据验证工具
 * 提供前端表单验证、后端数据校验、错误处理等功能
 */

import { z } from 'zod';

// 基础验证规则
export const validationRules = {
  required: (message: string = '此字段为必填项') => z.string().min(1, message),
  email: (message: string = '请输入有效的邮箱地址') => z.string().email(message),
  url: (message: string = '请输入有效的URL') => z.string().url(message),
  minLength: (min: number, message?: string) => 
    z.string().min(min, message || `至少需要${min}个字符`),
  maxLength: (max: number, message?: string) => 
    z.string().max(max, message || `最多${max}个字符`),
  number: (message: string = '请输入有效数字') => z.number(message),
  positiveNumber: (message: string = '请输入正数') => z.number().positive(message),
  integer: (message: string = '请输入整数') => z.number().int(message),
  boolean: (message: string = '请输入布尔值') => z.boolean(message),
  date: (message: string = '请输入有效日期') => z.date(message),
  array: (message: string = '请输入数组') => z.array(z.any(), message),
  object: (message: string = '请输入对象') => z.object({}),
};

// SKU 验证规则
export const skuValidationSchema = z.object({
  sku: validationRules.required('SKU编码不能为空')
    .min(3, 'SKU编码至少需要3个字符')
    .max(50, 'SKU编码最多50个字符')
    .regex(/^[A-Z0-9-_]+$/, 'SKU编码只能包含大写字母、数字、下划线和连字符'),
  name: validationRules.required('SKU名称不能为空')
    .min(2, 'SKU名称至少需要2个字符')
    .max(100, 'SKU名称最多100个字符'),
  product_id: validationRules.required('产品ID不能为空'),
  price: validationRules.number('价格必须是数字')
    .positive('价格必须是正数')
    .optional(),
  cost_price: validationRules.number('成本价必须是数字')
    .positive('成本价必须是正数')
    .optional(),
  weight: validationRules.number('重量必须是数字')
    .positive('重量必须是正数')
    .optional(),
  is_active: validationRules.boolean().default(true),
  attributes: z.record(z.any()).optional(),
  dimensions: z.record(z.any()).optional(),
});

// 产品分类验证规则
export const categoryValidationSchema = z.object({
  category_code: validationRules.required('分类编码不能为空')
    .min(2, '分类编码至少需要2个字符')
    .max(50, '分类编码最多50个字符')
    .regex(/^[a-z0-9-_]+$/, '分类编码只能包含小写字母、数字、下划线和连字符'),
  category_name: validationRules.required('分类名称不能为空')
    .min(2, '分类名称至少需要2个字符')
    .max(100, '分类名称最多100个字符'),
  description: z.string().max(500, '描述最多500个字符').optional(),
  parent_category_ids: z.array(z.number()).optional(),
  is_root: validationRules.boolean().default(false),
  sort_order: validationRules.integer('排序必须是整数').default(0),
});

// 维度模板验证规则
export const dimensionTemplateValidationSchema = z.object({
  dimension_code: validationRules.required('维度编码不能为空')
    .min(2, '维度编码至少需要2个字符')
    .max(50, '维度编码最多50个字符')
    .regex(/^[a-z0-9-_]+$/, '维度编码只能包含小写字母、数字、下划线和连字符'),
  dimension_name: validationRules.required('维度名称不能为空')
    .min(2, '维度名称至少需要2个字符')
    .max(100, '维度名称最多100个字符'),
  dimension_type: z.enum(['select', 'text', 'number', 'boolean', 'date'], {
    errorMap: () => ({ message: '维度类型必须是: select, text, number, boolean, date 之一' })
  }),
  description: z.string().max(500, '描述最多500个字符').optional(),
  sort_order: validationRules.integer('排序必须是整数').default(0),
});

// 维度值验证规则
export const dimensionValueValidationSchema = z.object({
  value_code: validationRules.required('维度值编码不能为空')
    .min(1, '维度值编码至少需要1个字符')
    .max(50, '维度值编码最多50个字符'),
  value_name: validationRules.required('维度值名称不能为空')
    .min(1, '维度值名称至少需要1个字符')
    .max(100, '维度值名称最多100个字符'),
  value_type: z.enum(['string', 'number', 'boolean', 'date'], {
    errorMap: () => ({ message: '维度值类型必须是: string, number, boolean, date 之一' })
  }),
  is_default: validationRules.boolean().default(false),
  sort_order: validationRules.integer('排序必须是整数').default(0),
});

// 产品验证规则
export const productValidationSchema = z.object({
  title: validationRules.required('产品标题不能为空')
    .min(2, '产品标题至少需要2个字符')
    .max(200, '产品标题最多200个字符'),
  handle: z.string()
    .min(2, '产品句柄至少需要2个字符')
    .max(100, '产品句柄最多100个字符')
    .regex(/^[a-z0-9-_]+$/, '产品句柄只能包含小写字母、数字、下划线和连字符')
    .optional(),
  description: z.string().max(1000, '描述最多1000个字符').optional(),
  product_type: z.string().max(50, '产品类型最多50个字符').optional(),
  vendor: z.string().max(100, '供应商最多100个字符').optional(),
  status: z.enum(['draft', 'active', 'inactive', 'archived'], {
    errorMap: () => ({ message: '状态必须是: draft, active, inactive, archived 之一' })
  }).default('draft'),
  is_active: validationRules.boolean().default(true),
  is_available: validationRules.boolean().default(true),
});

// 验证错误处理
export class ValidationError extends Error {
  public errors: Record<string, string[]>;
  
  constructor(errors: Record<string, string[]>) {
    super('Validation failed');
    this.name = 'ValidationError';
    this.errors = errors;
  }
}

// 验证函数
export function validateData<T>(schema: z.ZodSchema<T>, data: unknown): T {
  try {
    return schema.parse(data);
  } catch (error) {
    if (error instanceof z.ZodError) {
      const errors: Record<string, string[]> = {};
      error.errors.forEach((err) => {
        const path = err.path.join('.');
        if (!errors[path]) {
          errors[path] = [];
        }
        errors[path].push(err.message);
      });
      throw new ValidationError(errors);
    }
    throw error;
  }
}

// 异步验证函数
export async function validateDataAsync<T>(
  schema: z.ZodSchema<T>, 
  data: unknown
): Promise<T> {
  try {
    return await schema.parseAsync(data);
  } catch (error) {
    if (error instanceof z.ZodError) {
      const errors: Record<string, string[]> = {};
      error.errors.forEach((err) => {
        const path = err.path.join('.');
        if (!errors[path]) {
          errors[path] = [];
        }
        errors[path].push(err.message);
      });
      throw new ValidationError(errors);
    }
    throw error;
  }
}

// 表单验证Hook
export function useFormValidation<T>(
  schema: z.ZodSchema<T>,
  initialData?: Partial<T>
) {
  const [data, setData] = React.useState<Partial<T>>(initialData || {});
  const [errors, setErrors] = React.useState<Record<string, string[]>>({});
  const [isValid, setIsValid] = React.useState(false);

  const validate = React.useCallback(() => {
    try {
      const validatedData = validateData(schema, data);
      setErrors({});
      setIsValid(true);
      return validatedData;
    } catch (error) {
      if (error instanceof ValidationError) {
        setErrors(error.errors);
        setIsValid(false);
        return null;
      }
      throw error;
    }
  }, [schema, data]);

  const updateField = React.useCallback((field: keyof T, value: any) => {
    setData(prev => ({ ...prev, [field]: value }));
    // 清除该字段的错误
    if (errors[field as string]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field as string];
        return newErrors;
      });
    }
  }, [errors]);

  const clearErrors = React.useCallback(() => {
    setErrors({});
  }, []);

  const reset = React.useCallback(() => {
    setData(initialData || {});
    setErrors({});
    setIsValid(false);
  }, [initialData]);

  return {
    data,
    errors,
    isValid,
    validate,
    updateField,
    clearErrors,
    reset,
  };
}

// 导入React（如果还没有导入）
import React from 'react';
