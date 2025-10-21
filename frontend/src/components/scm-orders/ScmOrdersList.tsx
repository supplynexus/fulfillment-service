'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Button,
  TextField,
  InputAdornment,
  Pagination,
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
  Checkbox,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  FilterList as FilterIcon,
  LocalShipping as ShippingIcon,
  Delete as DeleteIcon,
  Sync as SyncIcon,
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { frontendApi } from '@/lib/api';

const ITEMS_PER_PAGE = 10;

interface ScmOrder {
  id_hashid: string;
  source_order_id_hashid?: string;
  scm_order_number?: string;
  status: string;
  fulfillment_status?: string;
  routing_strategy?: string;
  line_items: any[];
  currency: string;
  customer_email: string;
  customer_name?: string;
  customer_phone?: string;
  shipping_address: any;
  billing_address?: any;
  routing_metadata?: any;
  tracking_number?: string;
  tracking_url?: string;
  carrier?: string;
  shipped_at?: string;
  delivered_at?: string;
  error_message?: string;
  retry_count: number;
  last_retry_at?: string;
  created_at: string;
  updated_at?: string;
}

export function ScmOrdersList() {
  console.log('🔍 ScmOrdersList 组件文件加载');
  
  const router = useRouter();
  const [orders, setOrders] = useState<ScmOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  
  // 删除相关状态
  const [selectedOrders, setSelectedOrders] = useState<Set<string>>(new Set());
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingOrders, setDeletingOrders] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);
  
  // 批量更新 Shopify fulfillment 相关状态
  const [bulkUpdating, setBulkUpdating] = useState(false);
  const [updateDialogOpen, setUpdateDialogOpen] = useState(false);

  console.log('🔍 ScmOrdersList 组件渲染，当前状态:', {
    orders: orders.length,
    loading,
    error,
    searchTerm,
    currentPage,
    totalPages
  });

  const fetchScmOrders = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await frontendApi.get('/api/scm-orders', {
        params: {
          page: currentPage,
          limit: ITEMS_PER_PAGE,
          search: searchTerm || undefined,
        },
      });

      console.log('🔍 SCM订单API响应:', response.data);
      console.log('🔍 SCM订单数据:', response.data.scm_orders);
      console.log('🔍 SCM订单数量:', response.data.scm_orders?.length || 0);
      
      setOrders(response.data.scm_orders || []);
      setTotalPages(Math.ceil((response.data.total || 0) / ITEMS_PER_PAGE));
    } catch (err: any) {
      console.error('Failed to fetch SCM orders:', err);
      setError(err.response?.data?.detail || 'Failed to fetch SCM orders');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScmOrders();
  }, [currentPage, searchTerm]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
    setCurrentPage(1);
  };

  const handleRefresh = () => {
    fetchScmOrders();
  };


  const handleViewOrder = (orderHashid: string) => {
    router.push(`/scm-orders/${orderHashid}`);
  };

  // 删除相关处理函数
  const handleSelectOrder = (orderHashid: string) => {
    const newSelected = new Set(selectedOrders);
    if (newSelected.has(orderHashid)) {
      newSelected.delete(orderHashid);
    } else {
      newSelected.add(orderHashid);
    }
    setSelectedOrders(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedOrders.size === orders.length) {
      setSelectedOrders(new Set());
    } else {
      setSelectedOrders(new Set(orders.map(order => order.id_hashid)));
    }
  };

  const handleDeleteOrder = async (orderHashid: string) => {
    try {
      setDeletingOrders(true);
      await frontendApi.delete(`/api/scm-orders/${orderHashid}`);
      await fetchScmOrders();
      console.log('✅ SCM 订单删除成功');
    } catch (error: any) {
      console.error('❌ SCM 订单删除失败:', error);
      setError(error.response?.data?.detail || '删除失败');
    } finally {
      setDeletingOrders(false);
    }
  };

  const handleBulkDelete = () => {
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    try {
      setBulkDeleting(true);
      const deletePromises = Array.from(selectedOrders).map(orderHashid =>
        frontendApi.delete(`/api/scm-orders/${orderHashid}`)
      );
      await Promise.all(deletePromises);
      setSelectedOrders(new Set());
      setDeleteDialogOpen(false);
      await fetchScmOrders();
      console.log('✅ 批量删除 SCM 订单成功');
    } catch (error: any) {
      console.error('❌ 批量删除 SCM 订单失败:', error);
      setError(error.response?.data?.detail || '批量删除失败');
    } finally {
      setBulkDeleting(false);
    }
  };

  // 批量更新 Shopify fulfillment 处理函数
  const handleBulkUpdateShopifyFulfillment = () => {
    setUpdateDialogOpen(true);
  };

  const handleConfirmUpdate = async () => {
    try {
      setBulkUpdating(true);
      setError(null);
      
      const response = await frontendApi.post('/api/scm-orders/batch-update-shopify-fulfillment', {
        scm_order_hashids: Array.from(selectedOrders)
      });
      
      console.log('✅ 批量更新 Shopify fulfillment 成功:', response.data);
      
      // 显示成功消息
      const results = response.data.results;
      const successCount = results.success.length;
      const failedCount = results.failed.length;
      const skippedCount = response.data.skipped_orders?.length || 0;
      
      let message = `更新完成: ${successCount} 个成功`;
      if (failedCount > 0) {
        message += `, ${failedCount} 个失败`;
      }
      if (skippedCount > 0) {
        message += `, ${skippedCount} 个跳过（缺少跟踪号）`;
      }
      
      if (failedCount > 0 || skippedCount > 0) {
        setError(message);
      } else {
        setError(null);
      }
      
      setSelectedOrders(new Set());
      setUpdateDialogOpen(false);
      await fetchScmOrders();
      
    } catch (error: any) {
      console.error('❌ 批量更新 Shopify fulfillment 失败:', error);
      
      // 处理特定的业务逻辑错误
      const errorMessage = error.response?.data?.detail || '批量更新失败';
      if (errorMessage.includes('Shopify fulfillment order 已关闭')) {
        setError('该Shopify订单已经完全履行，无法再创建新的发货信息。这是正常的业务状态。');
      } else if (errorMessage.includes('没有匹配的 fulfillment order line items')) {
        setError('该Shopify订单的所有商品都已完全履行，无法再创建新的发货信息。');
      } else {
        setError(errorMessage);
      }
    } finally {
      setBulkUpdating(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'pending':
        return 'warning';
      case 'processing':
        return 'info';
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'cancelled':
        return 'error';
      default:
        return 'default';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading && orders.length === 0) {
    return (
      <Box
        display='flex'
        justifyContent='center'
        alignItems='center'
        minHeight='400px'
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box
        display='flex'
        justifyContent='space-between'
        alignItems='center'
        mb={3}
      >
        <Typography variant='h4' component='h1'>
          SCM 订单管理
        </Typography>
        <Box display='flex' gap={2}>
          <Button
            variant='outlined'
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
            disabled={loading}
          >
            刷新
          </Button>
        </Box>
      </Box>

      {/* 批量操作区域 */}
      {selectedOrders.size > 0 && (
        <Box sx={{ mb: 2, p: 2, bgcolor: 'action.hover', borderRadius: 1 }}>
          <Box display='flex' alignItems='center' gap={2}>
            <Typography variant='body2' color='text.secondary'>
              已选择 {selectedOrders.size} 个 SCM 订单
            </Typography>
            <Button
              variant='contained'
              color='primary'
              startIcon={bulkUpdating ? <CircularProgress size={16} /> : <SyncIcon />}
              onClick={handleBulkUpdateShopifyFulfillment}
              disabled={bulkUpdating || bulkDeleting}
            >
              {bulkUpdating ? '更新中...' : '更新 Shopify 发货'}
            </Button>
            <Button
              variant='contained'
              color='error'
              startIcon={bulkDeleting ? <CircularProgress size={16} /> : <DeleteIcon />}
              onClick={handleBulkDelete}
              disabled={bulkDeleting || bulkUpdating}
            >
              {bulkDeleting ? '删除中...' : '删除订单'}
            </Button>
            <Button
              variant='outlined'
              onClick={() => setSelectedOrders(new Set())}
              disabled={bulkDeleting || bulkUpdating}
            >
              取消选择
            </Button>
          </Box>
        </Box>
      )}

      {error && (
        <Alert severity='error' sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}


      <Card>
        <CardContent>
          <Box display='flex' gap={2} mb={3}>
            <TextField
              fullWidth
              placeholder='搜索 SCM 订单ID、订单ID或提供商...'
              value={searchTerm}
              onChange={handleSearch}
              InputProps={{
                startAdornment: (
                  <InputAdornment position='start'>
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
            <Button variant='outlined' startIcon={<FilterIcon />} disabled>
              筛选
            </Button>
          </Box>

          <TableContainer component={Paper} variant='outlined'>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={selectedOrders.size === orders.length && orders.length > 0}
                      indeterminate={selectedOrders.size > 0 && selectedOrders.size < orders.length}
                      onChange={handleSelectAll}
                    />
                  </TableCell>
                  <TableCell>SCM 订单ID</TableCell>
                  <TableCell>目标系统</TableCell>
                  <TableCell>目标系统ID</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell>履行状态</TableCell>
                  <TableCell>客户信息</TableCell>
                  <TableCell>总金额</TableCell>
                  <TableCell>物流信息</TableCell>
                  <TableCell>创建时间</TableCell>
                  <TableCell>操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {orders.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={11} align='center'>
                      <Typography variant='body2' color='text.secondary'>
                        {searchTerm
                          ? '没有找到匹配的 SCM 订单'
                          : '暂无 SCM 订单数据'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  orders.map(order => (
                    <TableRow key={order.id_hashid} hover>
                      <TableCell padding="checkbox">
                        <Checkbox
                          checked={selectedOrders.has(order.id_hashid)}
                          onChange={() => handleSelectOrder(order.id_hashid)}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2' fontWeight='medium'>
                          {order.scm_order_number || order.id_hashid}
                        </Typography>
                        {order.scm_order_number && (
                          <Typography variant='caption' color='text.secondary'>
                            ID: {order.id_hashid}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2' fontWeight='medium'>
                          CORE
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2' fontWeight='medium' fontFamily="monospace">
                          N/A
                        </Typography>
                        {order.routing_metadata?.printify_order_id && (
                          <Typography variant='caption' color='text.secondary'>
                            Printify: {order.routing_metadata.printify_order_id}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={order.status}
                          color={getStatusColor(order.status) as any}
                          size='small'
                        />
                      </TableCell>
                      <TableCell>
                        {order.fulfillment_status ? (
                          <Chip
                            label={order.fulfillment_status}
                            color={getStatusColor(order.fulfillment_status) as any}
                            size='small'
                          />
                        ) : (
                          <Typography variant='body2' color='text.secondary'>
                            N/A
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Box>
                          <Typography variant='body2' fontWeight='medium'>
                            {order.customer_name || 'N/A'}
                          </Typography>
                          <Typography variant='caption' color='text.secondary'>
                            {order.customer_email}
                          </Typography>
                          {order.customer_phone && (
                            <Typography variant='caption' color='text.secondary' display='block'>
                              {order.customer_phone}
                            </Typography>
                          )}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2' fontWeight='medium'>
                          {order.currency} N/A
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {order.tracking_number ? (
                          <Box>
                            <Typography variant='body2' fontFamily="monospace" fontSize="0.75rem">
                              {order.tracking_number}
                            </Typography>
                            {order.tracking_url && (
                              <Button
                                size="small"
                                href={order.tracking_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                variant="outlined"
                                sx={{ mt: 0.5, fontSize: '0.7rem', py: 0.2 }}
                              >
                                查看
                              </Button>
                            )}
                 {/* 显示物流公司、发货时间、送达时间 */}
                 <Box sx={{ mt: 1, fontSize: '0.7rem', color: 'text.secondary' }}>
                   <Typography variant="caption" display="block">
                     物流公司: {order.carrier || order.routing_metadata?.shipments?.[0]?.carrier || '未提供'}
                   </Typography>
                   <Typography variant="caption" display="block">
                     发货时间: {order.shipped_at ? new Date(order.shipped_at).toLocaleString('zh-CN') : order.routing_metadata?.shipments?.[0]?.shipped_at ? new Date(order.routing_metadata.shipments[0].shipped_at).toLocaleString('zh-CN') : '未发货'}
                   </Typography>
                   <Typography variant="caption" display="block">
                     送达时间: {order.delivered_at ? new Date(order.delivered_at).toLocaleString('zh-CN') : order.routing_metadata?.shipments?.[0]?.delivered_at ? new Date(order.routing_metadata.shipments[0].delivered_at).toLocaleString('zh-CN') : '未送达'}
                   </Typography>
                 </Box>
                          </Box>
                        ) : (
                          <Typography variant='body2' color='text.secondary'>
                            无物流信息
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {formatDate(order.created_at)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box display='flex' gap={1}>
                          <Tooltip title='查看详情'>
                            <IconButton
                              size='small'
                              onClick={() => handleViewOrder(order.id_hashid)}
                            >
                              <ViewIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title='删除订单'>
                            <IconButton
                              size='small'
                              onClick={() => handleDeleteOrder(order.id_hashid)}
                              disabled={deletingOrders}
                              color='error'
                            >
                              {deletingOrders ? <CircularProgress size={16} /> : <DeleteIcon />}
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>

          {totalPages > 1 && (
            <Box display='flex' justifyContent='center' mt={3}>
              <Pagination
                count={totalPages}
                page={currentPage}
                onChange={(_, page) => setCurrentPage(page)}
                color='primary'
              />
            </Box>
          )}
        </CardContent>
      </Card>

      {/* 删除确认对话框 */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          确认删除 SCM 订单
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" gutterBottom>
            您确定要删除选中的 {selectedOrders.size} 个 SCM 订单吗？
          </Typography>
          <Typography variant="body2" color="text.secondary">
            此操作不可撤销，删除的 SCM 订单将从数据库中永久移除。
          </Typography>
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              将要删除的 SCM 订单：
            </Typography>
            <Box sx={{ maxHeight: '200px', overflow: 'auto' }}>
              {Array.from(selectedOrders).map(orderHashid => {
                const order = orders.find(o => o.id_hashid === orderHashid);
                return order ? (
                  <Typography key={orderHashid} variant="body2" color="text.secondary">
                    • {order.scm_order_number || orderHashid} - {order.customer_name || order.customer_email}
                  </Typography>
                ) : null;
              })}
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>
            取消
          </Button>
          <Button
            variant="contained"
            color="error"
            startIcon={bulkDeleting ? <CircularProgress size={16} /> : <DeleteIcon />}
            onClick={handleConfirmDelete}
            disabled={bulkDeleting}
          >
            {bulkDeleting ? '删除中...' : '确认删除'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 更新 Shopify fulfillment 确认对话框 */}
      <Dialog
        open={updateDialogOpen}
        onClose={() => setUpdateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          确认更新 Shopify 发货信息
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" gutterBottom>
            您确定要更新选中的 {selectedOrders.size} 个 SCM 订单的 Shopify 发货信息吗？
          </Typography>
          <Typography variant="body2" color="text.secondary">
            此操作将把 SCM 订单的物流信息同步到对应的 Shopify 订单中。
          </Typography>
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              将要更新的 SCM 订单：
            </Typography>
            <Box sx={{ maxHeight: '200px', overflow: 'auto' }}>
              {Array.from(selectedOrders).map(orderHashid => {
                const order = orders.find(o => o.id_hashid === orderHashid);
                return order ? (
                  <Typography key={orderHashid} variant="body2" color="text.secondary">
                    • {order.scm_order_number || orderHashid} - {order.customer_name || order.customer_email}
                    {order.tracking_number && (
                      <span> (跟踪号: {order.tracking_number})</span>
                    )}
                  </Typography>
                ) : null;
              })}
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUpdateDialogOpen(false)}>
            取消
          </Button>
          <Button
            variant="contained"
            color="primary"
            startIcon={bulkUpdating ? <CircularProgress size={16} /> : <SyncIcon />}
            onClick={handleConfirmUpdate}
            disabled={bulkUpdating}
          >
            {bulkUpdating ? '更新中...' : '确认更新'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
