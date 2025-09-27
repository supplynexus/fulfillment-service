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

      // 模拟数据 - 实际应该从 API 获取
      const mockStats: MappingStats[] = [
        {
          platform: 'shopify',
          totalMappings: 45,
          activeMappings: 42,
          pendingMappings: 3,
          lastSync: '2025-09-28T10:30:00Z',
        },
        {
          platform: 'yahoo',
          totalMappings: 23,
          activeMappings: 20,
          pendingMappings: 3,
          lastSync: '2025-09-28T09:15:00Z',
        },
        {
          platform: 'rakuten',
          totalMappings: 18,
          activeMappings: 15,
          pendingMappings: 3,
          lastSync: '2025-09-28T08:45:00Z',
        },
      ];

      const mockRecentMappings: RecentMapping[] = [
        {
          id: '1',
          coreProduct: 'Unisex Oversized Boxy Tee',
          externalProduct: 'Trump crying',
          platform: 'shopify',
          status: 'active',
          createdAt: '2025-09-28T10:30:00Z',
        },
        {
          id: '2',
          coreProduct: 'Basic T-Shirt',
          externalProduct: 'Basic White T-Shirt',
          platform: 'yahoo',
          status: 'pending',
          createdAt: '2025-09-28T09:15:00Z',
        },
        {
          id: '3',
          coreProduct: 'Hoodie',
          externalProduct: 'Pullover Hoodie',
          platform: 'rakuten',
          status: 'active',
          createdAt: '2025-09-28T08:45:00Z',
        },
      ];

      setStats(mockStats);
      setRecentMappings(mockRecentMappings);
    } catch (err: any) {
      console.error('Failed to fetch mapping data:', err);
      setError(err.message || 'Failed to fetch mapping data');
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
                            <IconButton size="small">
                              <ViewIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="编辑">
                            <IconButton size="small">
                              <EditIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="删除">
                            <IconButton size="small" color="error">
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
