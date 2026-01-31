/**
 * PIM 系统 E2E 测试
 * 
 * 测试完整的产品信息管理工作流程：
 * 1. 用户登录
 * 2. 创建产品分类
 * 3. 创建维度模板
 * 4. 创建SKU
 * 5. 验证数据一致性
 */

import { test, expect } from '@playwright/test'

test.describe('PIM 系统 E2E 测试', () => {
  test.beforeEach(async ({ page }) => {
    // 模拟登录状态
    await page.goto('/login')
    
    // 模拟JWT token
    await page.evaluate(() => {
      localStorage.setItem('token', 'mock-jwt-token')
    })
    
    // 导航到PIM页面
    await page.goto('/product-categories')
  })

  test('完整的产品分类管理工作流程', async ({ page }) => {
    // 1. 验证页面加载
    await expect(page.getByText('产品分类管理')).toBeVisible()
    await expect(page.getByText('创建分类')).toBeVisible()

    // 2. 创建新分类
    await page.click('text=创建分类')
    
    // 等待对话框打开
    await expect(page.getByText('创建分类')).toBeVisible()
    
    // 填写分类信息
    await page.fill('input[name="name"]', '测试分类')
    await page.fill('input[name="code"]', 'test-category')
    await page.fill('textarea[name="description"]', '测试分类描述')
    
    // 提交表单
    await page.click('button[type="submit"]')
    
    // 验证创建成功
    await expect(page.getByText('测试分类')).toBeVisible()
    await expect(page.getByText('test-category')).toBeVisible()

    // 3. 编辑分类
    await page.click('button:has-text("编辑")')
    
    // 等待编辑对话框打开
    await expect(page.getByText('编辑分类')).toBeVisible()
    
    // 修改分类名称
    await page.fill('input[name="name"]', '更新后的测试分类')
    
    // 提交更新
    await page.click('button[type="submit"]')
    
    // 验证更新成功
    await expect(page.getByText('更新后的测试分类')).toBeVisible()

    // 4. 删除分类
    await page.click('button:has-text("删除")')
    
    // 确认删除
    await page.click('button:has-text("确认")')
    
    // 验证删除成功
    await expect(page.getByText('更新后的测试分类')).not.toBeVisible()
  })

  test('完整的SKU管理工作流程', async ({ page }) => {
    // 导航到SKU页面
    await page.goto('/skus')
    
    // 验证页面加载
    await expect(page.getByText('SKU 管理')).toBeVisible()
    await expect(page.getByText('创建 SKU')).toBeVisible()

    // 1. 创建新SKU
    await page.click('text=创建 SKU')
    
    // 等待对话框打开
    await expect(page.getByText('创建 SKU')).toBeVisible()
    
    // 填写SKU信息
    await page.fill('input[name="sku"]', 'TEST-SKU-001')
    await page.fill('input[name="name"]', '测试产品')
    await page.fill('input[name="price"]', '29.99')
    await page.fill('input[name="cost"]', '15.00')
    await page.fill('input[name="stock"]', '100')
    
    // 提交表单
    await page.click('button[type="submit"]')
    
    // 验证创建成功
    await expect(page.getByText('TEST-SKU-001')).toBeVisible()
    await expect(page.getByText('测试产品')).toBeVisible()

    // 2. 编辑SKU
    await page.click('button:has-text("编辑")')
    
    // 等待编辑对话框打开
    await expect(page.getByText('编辑 SKU')).toBeVisible()
    
    // 修改SKU信息
    await page.fill('input[name="name"]', '更新后的测试产品')
    await page.fill('input[name="price"]', '39.99')
    
    // 提交更新
    await page.click('button[type="submit"]')
    
    // 验证更新成功
    await expect(page.getByText('更新后的测试产品')).toBeVisible()

    // 3. 删除SKU
    await page.click('button:has-text("删除")')
    
    // 确认删除
    await page.click('button:has-text("确认")')
    
    // 验证删除成功
    await expect(page.getByText('更新后的测试产品')).not.toBeVisible()
  })

  test('SKU批量创建工作流程', async ({ page }) => {
    // 导航到SKU批量创建页面
    await page.goto('/skus/batch-create')
    
    // 验证页面加载
    await expect(page.getByText('SKU 批量创建')).toBeVisible()
    await expect(page.getByText('选择产品')).toBeVisible()

    // 1. 选择产品
    await page.click('text=选择产品')
    
    // 等待产品选择对话框打开
    await expect(page.getByText('选择产品')).toBeVisible()
    
    // 选择产品
    await page.click('input[type="checkbox"]')
    
    // 确认选择
    await page.click('button:has-text("确认")')
    
    // 2. 选择维度
    await page.click('text=选择维度')
    
    // 等待维度选择对话框打开
    await expect(page.getByText('选择维度')).toBeVisible()
    
    // 选择维度
    await page.click('input[type="checkbox"]')
    
    // 确认选择
    await page.click('button:has-text("确认")')
    
    // 3. 预览SKU
    await page.click('text=预览 SKU')
    
    // 验证预览
    await expect(page.getByText('SKU 预览')).toBeVisible()
    
    // 4. 生成SKU
    await page.click('text=生成 SKU')
    
    // 验证生成成功
    await expect(page.getByText('SKU 生成成功')).toBeVisible()
  })

  test('维度模板管理工作流程', async ({ page }) => {
    // 导航到维度模板页面
    await page.goto('/dimension-templates')
    
    // 验证页面加载
    await expect(page.getByText('维度模板管理')).toBeVisible()
    await expect(page.getByText('创建模板')).toBeVisible()

    // 1. 创建新模板
    await page.click('text=创建模板')
    
    // 等待对话框打开
    await expect(page.getByText('创建维度模板')).toBeVisible()
    
    // 填写模板信息
    await page.fill('input[name="dimensionCode"]', 'color')
    await page.fill('input[name="dimensionName"]', '颜色')
    await page.selectOption('select[name="dimensionType"]', 'select')
    await page.fill('textarea[name="description"]', '产品颜色维度')
    
    // 提交表单
    await page.click('button[type="submit"]')
    
    // 验证创建成功
    await expect(page.getByText('颜色')).toBeVisible()
    await expect(page.getByText('color')).toBeVisible()

    // 2. 管理维度值
    await page.click('button:has-text("管理值")')
    
    // 等待维度值管理对话框打开
    await expect(page.getByText('维度值管理')).toBeVisible()
    
    // 添加维度值
    await page.click('text=添加值')
    
    // 填写维度值信息
    await page.fill('input[name="value"]', '红色')
    await page.fill('input[name="displayName"]', '红色')
    await page.fill('input[name="sortOrder"]', '1')
    
    // 保存维度值
    await page.click('button:has-text("保存")')
    
    // 验证维度值添加成功
    await expect(page.getByText('红色')).toBeVisible()

    // 3. 删除模板
    await page.click('button:has-text("删除")')
    
    // 确认删除
    await page.click('button:has-text("确认")')
    
    // 验证删除成功
    await expect(page.getByText('颜色')).not.toBeVisible()
  })

  test('错误处理和用户反馈', async ({ page }) => {
    // 测试网络错误处理
    await page.route('**/api/product-categories', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: '服务器错误' })
      })
    })

    // 导航到产品分类页面
    await page.goto('/product-categories')
    
    // 验证错误消息显示
    await expect(page.getByText('加载产品分类失败')).toBeVisible()

    // 测试表单验证
    await page.click('text=创建分类')
    
    // 尝试提交空表单
    await page.click('button[type="submit"]')
    
    // 验证验证错误消息
    await expect(page.getByText('此字段为必填项')).toBeVisible()
  })

  test('响应式设计和移动端适配', async ({ page }) => {
    // 设置移动端视口
    await page.setViewportSize({ width: 375, height: 667 })
    
    // 导航到产品分类页面
    await page.goto('/product-categories')
    
    // 验证移动端布局
    await expect(page.getByText('产品分类管理')).toBeVisible()
    
    // 测试移动端菜单
    await page.click('button[aria-label="打开菜单"]')
    await expect(page.getByText('创建分类')).toBeVisible()
    
    // 测试移动端表单
    await page.click('text=创建分类')
    
    // 验证移动端表单布局
    await expect(page.getByText('创建分类')).toBeVisible()
    
    // 填写表单
    await page.fill('input[name="name"]', '移动端测试分类')
    await page.fill('input[name="code"]', 'mobile-test')
    
    // 提交表单
    await page.click('button[type="submit"]')
    
    // 验证创建成功
    await expect(page.getByText('移动端测试分类')).toBeVisible()
  })
})
