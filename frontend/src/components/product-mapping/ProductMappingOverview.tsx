'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
  Chip,
  Avatar,
  LinearProgress,
  Alert,
  CircularProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Link as LinkIcon,
  Storefront as ShopifyIcon,
  Public as YahooIcon,
  Storefront as RakutenIcon,
  TrendingUp as TrendingUpIcon,
  Refresh as RefreshIcon,
  Visibility as ViewIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { frontendApi } from '@/lib/api';

interface MappingStats {
  platform: string;
  totalMappings: number;
  activeMappings: number;
  pendingMappings: number;
  lastSync: string;
}

interface RecentMapping {
  id: string;
  coreProduct: string;
  externalProduct: string;
  platform: string;
  status: 'active' | 'pending' | 'error';
  createdAt: string;
}

export function ProductMappingOverview() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<MappingStats[]>([]);
  const [recentMappings, setRecentMappings] = useState<RecentMapping[]>([]);

  const fetchMappingData = async () => {
    try {
      setLoading(true);
      setError(null);

      // 获取核心商品数据
      const coreProductsResponse = await frontendApi.get('/api/products', {
        params: {
          page: 1,
          limit: 100,
          include_mappings: true,
        },
      });

      // 获取外部商品数据
      const externalProductsResponse = await frontendApi.get('/api/external-products', {
        params: {
          page: 1,
          limit: 100,
        },
      });

      const coreProducts = coreProductsResponse.data.products || [];
      const externalProducts = externalProductsResponse.data.products || [];

      // 计算映射统计
      const platformStats: { [key: string]: { total: number; active: number; pending: number; lastSync: string } } = {};
      
      // 初始化平台统计
      const platforms = ['shopify', 'yahoo', 'rakuten'];
      platforms.forEach(platform => {
        platformStats[platform] = {
          total: 0,
          active: 0,
          pending: 0,
          lastSync: new Date().toISOString(),
        };
      });

      // 统计核心商品的映射
      coreProducts.forEach((product: any) => {
        if (product.mappings && product.mappings.length > 0) {
          product.mappings.forEach((mapping: any) => {
            const platform = mapping.external_system_name?.toLowerCase() || 'unknown';
            if (platformStats[platform]) {
              platformStats[platform].total++;
              if (mapping.sync_status === 'active') {
                platformStats[platform].active++;
              } else if (mapping.sync_status === 'pending') {
                platformStats[platform].pending++;
              }
            }
          });
        }
      });

      // 转换为组件需要的格式
      const stats: MappingStats[] = Object.entries(platformStats).map(([platform, data]) => ({
        platform,
        totalMappings: data.total,
        activeMappings: data.active,
        pendingMappings: data.pending,
        lastSync: data.lastSync,
      }));

      // 生成最近映射记录
      const recentMappings: RecentMapping[] = [];
      coreProducts.forEach((product: any) => {
        if (product.mappings && product.mappings.length > 0) {
          product.mappings.forEach((mapping: any) => {
            const externalProduct = externalProducts.find((ep: any) => 
              ep.external_product_id === mapping.external_product_id
            );
            
            if (externalProduct) {
              recentMappings.push({
                id: mapping.id_hashid || mapping.id,
                coreProduct: product.title,
                externalProduct: externalProduct.title,
                platform: mapping.external_system_name?.toLowerCase() || 'unknown',
                status: mapping.sync_status === 'active' ? 'active' : 
                       mapping.sync_status === 'pending' ? 'pending' : 'error',
                createdAt: mapping.created_at || new Date().toISOString(),
              });
            }
          });
        }
      });

      // 按创建时间排序，取最近10条
      recentMappings.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
      const recentMappingsSlice = recentMappings.slice(0, 10);

      setStats(stats);
      setRecentMappings(recentMappingsSlice);
    } catch (err: any) {
      console.error('Failed to fetch mapping data:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to fetch mapping data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMappingData();
  }, []);

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case 'shopify':
        return <ShopifyIcon />;
      case 'yahoo':
        return <YahooIcon />;
      case 'rakuten':
        return <RakutenIcon />;
      default:
        return <LinkIcon />;
    }
  };

  const getPlatformColor = (platform: string) => {
    switch (platform) {
      case 'shopify':
        return '#96BF47';
      case 'yahoo':
        return '#FF6600';
      case 'rakuten':
        return '#BF0000';
      default:
        return '#1976d2';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'pending':
        return 'warning';
      case 'error':
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

  const handlePlatformClick = (platform: string) => {
    router.push(`/product-mapping/${platform}`);
  };

  const handleViewMapping = (mappingId: string) => {
    // TODO: 实现查看映射详情的功能
    console.log('View mapping:', mappingId);
  };

  const handleEditMapping = (mappingId: string) => {
    // TODO: 实现编辑映射的功能
    console.log('Edit mapping:', mappingId);
  };

  const handleDeleteMapping = async (mappingId: string) => {
    try {
      // TODO: 实现删除映射的 API 调用
      console.log('Delete mapping:', mappingId);
      // 刷新数据
      await fetchMappingData();
    } catch (err: any) {
      console.error('Failed to delete mapping:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to delete mapping');
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          商品映射总览
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={fetchMappingData}
          disabled={loading}
        >
          刷新数据
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* 平台统计卡片 */}
      <Grid container spacing={3} mb={3}>
        {stats.map((stat) => (
          <Grid item xs={12} md={4} key={stat.platform}>
            <Card 
              sx={{ 
                cursor: 'pointer',
                '&:hover': { 
                  boxShadow: 3,
                  transform: 'translateY(-2px)',
                  transition: 'all 0.2s ease-in-out'
                }
              }}
              onClick={() => handlePlatformClick(stat.platform)}
            >
              <CardContent>
                <Box display="flex" alignItems="center" mb={2}>
                  <Avatar
                    sx={{
                      bgcolor: getPlatformColor(stat.platform),
                      mr: 2,
                    }}
                  >
                    {getPlatformIcon(stat.platform)}
                  </Avatar>
                  <Typography variant="h6" component="div">
                    {stat.platform.charAt(0).toUpperCase() + stat.platform.slice(1)}
                  </Typography>
                </Box>
                
                <Box mb={2}>
                  <Typography variant="h4" component="div" color="primary">
                    {stat.totalMappings}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    总映射数
                  </Typography>
                </Box>

                <Box mb={2}>
                  <Box display="flex" justifyContent="space-between" mb={1}>
                    <Typography variant="body2">活跃映射</Typography>
                    <Typography variant="body2">{stat.activeMappings}</Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={(stat.activeMappings / stat.totalMappings) * 100}
                    sx={{ height: 6, borderRadius: 3 }}
                  />
                </Box>

                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Chip
                    label={`${stat.pendingMappings} 待处理`}
                    color="warning"
                    size="small"
                  />
                  <Typography variant="caption" color="text.secondary">
                    最后同步: {formatDate(stat.lastSync)}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* 最近映射记录 */}
      <Card>
        <CardContent>
          <Typography variant="h6" component="h2" mb={2}>
            最近映射记录
          </Typography>
          
          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>核心商品</TableCell>
                  <TableCell>外部商品</TableCell>
                  <TableCell>平台</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell>创建时间</TableCell>
                  <TableCell>操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {recentMappings.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography variant="body2" color="text.secondary">
                        暂无映射记录
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  recentMappings.map((mapping) => (
                    <TableRow key={mapping.id} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">
                          {mapping.coreProduct}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {mapping.externalProduct}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box display="flex" alignItems="center">
                          <Avatar
                            sx={{
                              bgcolor: getPlatformColor(mapping.platform),
                              width: 24,
                              height: 24,
                              mr: 1,
                            }}
                          >
                            {getPlatformIcon(mapping.platform)}
                          </Avatar>
                          <Typography variant="body2">
                            {mapping.platform.charAt(0).toUpperCase() + mapping.platform.slice(1)}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={mapping.status === 'active' ? '活跃' : mapping.status === 'pending' ? '待处理' : '错误'}
                          color={getStatusColor(mapping.status) as any}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {formatDate(mapping.createdAt)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box display="flex" gap={1}>
                          <Tooltip title="查看详情">
                            <IconButton 
                              size="small"
                              onClick={() => handleViewMapping(mapping.id)}
                            >
                              <ViewIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="编辑">
                            <IconButton 
                              size="small"
                              onClick={() => handleEditMapping(mapping.id)}
                            >
                              <EditIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="删除">
                            <IconButton 
                              size="small" 
                              color="error"
                              onClick={() => handleDeleteMapping(mapping.id)}
                            >
                              <DeleteIcon />
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
        </CardContent>
      </Card>
    </Box>
  );
}
