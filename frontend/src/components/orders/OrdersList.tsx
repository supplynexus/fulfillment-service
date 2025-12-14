'use client';

import React, { useState, useEffect, useCallback } from 'react';
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
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
  Pagination,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Checkbox,
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  FilterList as FilterIcon,
  Sync as SyncIcon,
  ArrowUpward as ArrowUpwardIcon,
  ArrowDownward as ArrowDownwardIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { useRouter } from 'next/navigation';
import { Order, OrderStatus } from '@/types/order';
import { frontendApi } from '@/lib/api';

const ITEMS_PER_PAGE = 20; // 每页显示20个订单

const getAddressValidationDisplay = (
  status: Order['address_validation_status'],
  reasonCode?: string
) => {
  if (!status || status === 'not_checked') {
    return {
      label: '未校验',
      color: 'default' as const,
      tooltip: '此订单的地址尚未进行自动校验',
    };
  }

  switch (status) {
    case 'valid':
      return {
        label: '地址正常',
        color: 'success' as const,
        tooltip: '地址通过基础规则校验',
      };
    case 'invalid':
      return {
        label: '地址有问题',
        color: 'error' as const,
        tooltip:
          '系统判断该地址存在明显问题，请在发货前人工确认（原因: ' +
          (reasonCode || '请查看详情') +
          '）',
      };
    case 'suspicious':
      return {
        label: '地址需确认',
        color: 'warning' as const,
        tooltip:
          '系统检测到地址存在潜在风险，建议在发货前确认（原因: ' +
          (reasonCode || '请查看详情') +
          '）',
      };
    case 'failed':
      return {
        label: '校验失败',
        color: 'info' as const,
        tooltip:
          '地址校验服务暂时失败，可能是系统或网络问题，并不代表地址本身有问题',
      };
    default:
      return {
        label: status,
        color: 'default' as const,
        tooltip: '地址校验状态: ' + status,
      };
  }
};

export function OrdersList() {
  const router = useRouter();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // 删除相关状态
  const [selectedOrders, setSelectedOrders] = useState<Set<string>>(new Set());
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingOrders, setDeletingOrders] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [bulkUpdating, setBulkUpdating] = useState(false);
  const [updateDialogOpen, setUpdateDialogOpen] = useState(false);
  const [sortBy, setSortBy] = useState<'created_at' | 'order_date'>(
    'created_at'
  );
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const fetchOrders = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await frontendApi.get('/api/orders', {
        params: {
          page: currentPage,
          limit: ITEMS_PER_PAGE,
          search: searchTerm || undefined,
          sort_by: sortBy,
          sort_order: sortOrder,
        },
      });

      console.log('🔍 前端接收到的订单数据:', {
        orders: response.data.orders?.length || 0,
        total: response.data.total,
        total_pages: response.data.total_pages,
        current_page: response.data.current_page,
        fullResponse: response.data,
      });

      setOrders(response.data.orders || []);
      setTotalPages(response.data.total_pages || 1);
      setTotalCount(response.data.total || 0);
    } catch (err: any) {
      console.error('Failed to fetch orders:', err);
      setError(err.response?.data?.detail || 'Failed to fetch orders');
    } finally {
      setLoading(false);
    }
  }, [currentPage, searchTerm, sortBy, sortOrder]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
    setCurrentPage(1); // 搜索时重置到第一页
  };

  const handleRefresh = () => {
    fetchOrders();
  };

  const handlePageChange = (
    event: React.ChangeEvent<unknown>,
    page: number
  ) => {
    setCurrentPage(page);
  };

  const handleSort = (field: 'created_at' | 'order_date') => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc'); // 默认降序
    }
    setCurrentPage(1); // 排序时重置到第一页
  };

  // 批量更新 Shopify 订单状态
  const handleBulkUpdateShopifyStatus = () => {
    if (selectedOrders.size === 0) {
      setError('请先选择要更新的订单');
      return;
    }
    setUpdateDialogOpen(true);
  };

  const handleConfirmUpdate = async () => {
    try {
      setBulkUpdating(true);
      setError(null);

      const response = await frontendApi.post('/api/orders/batch-update-shopify-status', {
        order_ids: Array.from(selectedOrders)
      });

      console.log('✅ 批量更新 Shopify 订单状态成功:', response.data);

      // 显示成功消息
      const results = response.data.results;
      const successCount = results.success.length;
      const failedCount = results.failed.length;

      let message = `更新完成: ${successCount} 个成功`;
      if (failedCount > 0) {
        message += `, ${failedCount} 个失败`;
      }

      if (failedCount > 0) {
        setError(message);
      } else {
        setError(null);
      }

      setSelectedOrders(new Set());
      setUpdateDialogOpen(false);
      await fetchOrders();

    } catch (error: any) {
      console.error('❌ 批量更新 Shopify 订单状态失败:', error);
      setError(error.response?.data?.detail || '批量更新失败');
    } finally {
      setBulkUpdating(false);
    }
  };

  const handleViewOrder = (orderId: string) => {
    router.push(`/orders/${orderId}`);
  };

  // 删除相关函数
  const handleSelectOrder = (orderId: string, checked: boolean) => {
    setSelectedOrders(prev => {
      const newSet = new Set(prev);
      if (checked) {
        newSet.add(orderId);
      } else {
        newSet.delete(orderId);
      }
      return newSet;
    });
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedOrders(new Set(orders.map(order => order.id_hashid)));
    } else {
      setSelectedOrders(new Set());
    }
  };

  const handleDeleteOrder = async (orderId: string) => {
    try {
      setDeletingOrders(prev => new Set(prev).add(orderId));

      const response = await frontendApi.delete(`/api/orders/${orderId}`);

      if (response.data.success) {
        // 删除成功后刷新列表
        fetchOrders();
        setError(null);
      } else {
        setError(`删除失败：${response.data.message || '未知错误'}`);
      }
    } catch (error: any) {
      console.error('❌ 删除订单失败:', error);
      setError(
        `删除失败：${error.response?.data?.detail || error.message || '网络错误'}`
      );
    } finally {
      setDeletingOrders(prev => {
        const newSet = new Set(prev);
        newSet.delete(orderId);
        return newSet;
      });
    }
  };

  const handleBulkDelete = async () => {
    if (selectedOrders.size === 0) {
      setError('请先选择要删除的订单');
      return;
    }

    setBulkDeleting(true);

    try {
      const deletePromises = Array.from(selectedOrders).map(async orderId => {
        try {
          const response = await frontendApi.delete(`/api/orders/${orderId}`);
          return { orderId, success: response.data.success };
        } catch (error: any) {
          return { orderId, success: false, error: error.message };
        }
      });

      const results = await Promise.all(deletePromises);
      const successful = results.filter(r => r.success).length;
      const failed = results.filter(r => !r.success).length;

      if (successful > 0) {
        // 删除成功后刷新列表
        fetchOrders();
        setSelectedOrders(new Set());
        setDeleteDialogOpen(false);
      }

      if (failed > 0) {
        setError(`批量删除完成：成功 ${successful} 个，失败 ${failed} 个`);
      }
    } catch (error: any) {
      console.error('❌ 批量删除失败:', error);
      setError(`批量删除失败：${error.message || '网络错误'}`);
    } finally {
      setBulkDeleting(false);
    }
  };

  const handleConfirmDelete = () => {
    if (selectedOrders.size === 0) {
      setError('请先选择要删除的订单');
      return;
    }
    setDeleteDialogOpen(true);
  };

  const getStatusColor = (status: OrderStatus) => {
    switch (status) {
      case OrderStatus.PENDING:
        return 'warning';
      case OrderStatus.PROCESSING:
        return 'info';
      case OrderStatus.FULFILLED:
        return 'success';
      case OrderStatus.CANCELLED:
        return 'error';
      case OrderStatus.FAILED:
        return 'error';
      case OrderStatus.REFUNDED:
        return 'default';
      default:
        return 'default';
    }
  };

  const getFulfillmentStatusColor = (
    fulfillmentStatus: string | null | undefined
  ) => {
    if (!fulfillmentStatus) return 'default';

    switch (fulfillmentStatus.toLowerCase()) {
      case 'fulfilled':
        return 'success';
      case 'partial':
        return 'warning';
      case 'unfulfilled':
        return 'default';
      case 'cancelled':
        return 'error';
      case 'in_progress':
        return 'info';
      default:
        return 'default';
    }
  };

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
    }).format(amount);
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
          订单管理
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

      {error && (
        <Alert severity='error' sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {syncMessage && (
        <Alert
          severity={
            syncMessage.includes('✅')
              ? 'success'
              : syncMessage.includes('⚠️')
                ? 'warning'
                : 'info'
          }
          sx={{ mb: 2 }}
        >
          {syncMessage}
        </Alert>
      )}

      <Card>
        <CardContent>
          <Box display='flex' gap={2} mb={3}>
            <TextField
              fullWidth
              placeholder='搜索订单ID、客户邮箱或订单号...'
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

          {/* 批量操作区域 */}
          {selectedOrders.size > 0 && (
            <Box sx={{ mb: 2, display: 'flex', gap: 1, alignItems: 'center' }}>
              <Button
                variant='contained'
                color='primary'
                startIcon={
                  bulkUpdating ? <CircularProgress size={16} /> : <SyncIcon />
                }
                onClick={handleBulkUpdateShopifyStatus}
                disabled={bulkUpdating}
              >
                {bulkUpdating ? '更新中...' : '同步更新 Shopify 订单状态'}
              </Button>
              <Button
                variant='contained'
                color='error'
                startIcon={
                  bulkDeleting ? <CircularProgress size={16} /> : <DeleteIcon />
                }
                onClick={handleConfirmDelete}
                disabled={bulkDeleting}
              >
                {bulkDeleting
                  ? '删除中...'
                  : `删除订单 (${selectedOrders.size})`}
              </Button>
              <Button
                variant='outlined'
                onClick={() => setSelectedOrders(new Set())}
              >
                取消选择
              </Button>
              <Typography variant='body2' color='text.secondary'>
                已选择 {selectedOrders.size} 个订单
              </Typography>
            </Box>
          )}

          <TableContainer component={Paper} variant='outlined'>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell padding='checkbox'>
                    <Checkbox
                      indeterminate={
                        selectedOrders.size > 0 &&
                        selectedOrders.size < orders.length
                      }
                      checked={
                        orders.length > 0 &&
                        selectedOrders.size === orders.length
                      }
                      onChange={e => handleSelectAll(e.target.checked)}
                    />
                  </TableCell>
                  <TableCell>订单ID</TableCell>
                  <TableCell>Shopify订单号</TableCell>
                  <TableCell>客户</TableCell>
                  <TableCell>金额</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell>履约状态</TableCell>
                  <TableCell>地址</TableCell>
                  <TableCell>
                    <Box display='flex' alignItems='center' gap={1}>
                      订单日期
                      <IconButton
                        size='small'
                        onClick={() => handleSort('order_date')}
                        color={sortBy === 'order_date' ? 'primary' : 'default'}
                      >
                        {sortBy === 'order_date' && sortOrder === 'desc' ? (
                          <ArrowDownwardIcon fontSize='small' />
                        ) : (
                          <ArrowUpwardIcon fontSize='small' />
                        )}
                      </IconButton>
                    </Box>
                  </TableCell>
                  <TableCell>操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {orders.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} align='center'>
                      <Typography variant='body2' color='text.secondary'>
                        {searchTerm ? '没有找到匹配的订单' : '暂无订单数据'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  orders.map(order => (
                    <TableRow key={order.id_hashid} hover>
                      <TableCell padding='checkbox'>
                        <Checkbox
                          checked={selectedOrders.has(order.id_hashid)}
                          onChange={e =>
                            handleSelectOrder(order.id_hashid, e.target.checked)
                          }
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2' fontWeight='medium'>
                          {order.order_number || order.id_hashid}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {order.external_order_name || order.external_order_id}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box>
                          <Typography variant='body2' fontWeight='medium'>
                            {order.customer_name || '未知客户'}
                          </Typography>
                          <Typography variant='caption' color='text.secondary'>
                            {order.customer_email}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2' fontWeight='medium'>
                          {formatCurrency(order.total_amount, order.currency)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={order.status}
                          color={getStatusColor(order.status) as any}
                          size='small'
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={order.fulfillment_status || 'unfulfilled'}
                          color={getFulfillmentStatusColor(
                            order.fulfillment_status
                          )}
                          size='small'
                        />
                      </TableCell>
                      <TableCell>
                        {(() => {
                          const {
                            label,
                            color,
                            tooltip,
                          } = getAddressValidationDisplay(
                            order.address_validation_status,
                            order.address_validation_reason_code
                          );
                          return (
                            <Tooltip title={tooltip}>
                              <Chip label={label} color={color as any} size='small' />
                            </Tooltip>
                          );
                        })()}
                      </TableCell>
                      <TableCell>
                        <Typography variant='body2'>
                          {formatDate(order.order_date)}
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
                              color='error'
                              onClick={() => handleDeleteOrder(order.id_hashid)}
                              disabled={deletingOrders.has(order.id_hashid)}
                            >
                              {deletingOrders.has(order.id_hashid) ? (
                                <CircularProgress size={16} />
                              ) : (
                                <DeleteIcon />
                              )}
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

          {/* 分页组件 */}
          <Box display='flex' justifyContent='center' mt={3}>
            <Stack spacing={2}>
              <Pagination
                count={totalPages}
                page={currentPage}
                onChange={handlePageChange}
                color='primary'
                showFirstButton
                showLastButton
              />
              <Typography
                variant='body2'
                color='text.secondary'
                textAlign='center'
              >
                共 {totalCount} 个订单，第 {currentPage} 页，共 {totalPages} 页
              </Typography>
            </Stack>
          </Box>
        </CardContent>
      </Card>

      {/* 更新 Shopify 订单状态确认对话框 */}
      <Dialog
        open={updateDialogOpen}
        onClose={() => setUpdateDialogOpen(false)}
        maxWidth='sm'
        fullWidth
      >
        <DialogTitle>
          确认同步更新 Shopify 订单状态
        </DialogTitle>
        <DialogContent>
          <Typography variant='body1' gutterBottom>
            您确定要同步更新选中的 {selectedOrders.size} 个订单的 Shopify 状态吗？
          </Typography>
          <Typography variant='body2' color='text.secondary'>
            此操作将从 Shopify 获取最新的履行信息并更新到核心订单中。
          </Typography>
          <Box sx={{ mt: 2 }}>
            <Typography variant='subtitle2' gutterBottom>
              将要更新的订单：
            </Typography>
            <Box sx={{ maxHeight: '200px', overflow: 'auto' }}>
              {Array.from(selectedOrders).map(orderId => {
                const order = orders.find(o => o.id_hashid === orderId);
                return order ? (
                  <Typography key={orderId} variant='body2' color='text.secondary'>
                    • {order.order_number || order.id_hashid} - {order.external_order_name || order.external_order_id}
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
            variant='contained'
            color='primary'
            startIcon={bulkUpdating ? <CircularProgress size={16} /> : <SyncIcon />}
            onClick={handleConfirmUpdate}
            disabled={bulkUpdating}
          >
            {bulkUpdating ? '更新中...' : '确认更新'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 删除确认对话框 */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        maxWidth='sm'
        fullWidth
      >
        <DialogTitle>确认删除订单</DialogTitle>
        <DialogContent>
          <Typography variant='body1' gutterBottom>
            您确定要删除选中的 {selectedOrders.size} 个订单吗？
          </Typography>
          <Typography variant='body2' color='text.secondary'>
            此操作不可撤销，删除的订单将从数据库中永久移除。
          </Typography>
          <Box sx={{ mt: 2 }}>
            <Typography variant='subtitle2' gutterBottom>
              将要删除的订单：
            </Typography>
            <Box sx={{ maxHeight: '200px', overflow: 'auto' }}>
              {Array.from(selectedOrders).map(orderId => {
                const order = orders.find(o => o.id_hashid === orderId);
                return order ? (
                  <Typography
                    key={orderId}
                    variant='body2'
                    color='text.secondary'
                  >
                    • {order.order_number || order.id_hashid} -{' '}
                    {order.external_order_name || order.external_order_id}
                  </Typography>
                ) : null;
              })}
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>取消</Button>
          <Button
            variant='contained'
            color='error'
            startIcon={
              bulkDeleting ? <CircularProgress size={16} /> : <DeleteIcon />
            }
            onClick={handleBulkDelete}
            disabled={bulkDeleting}
          >
            {bulkDeleting ? '删除中...' : '确认删除'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
