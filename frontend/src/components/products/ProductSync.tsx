'use client';

import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Alert,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Divider,
  Paper,
} from '@mui/material';
import {
  Sync as SyncIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { frontendApi } from '@/lib/api';
import toast from 'react-hot-toast';

interface SyncResult {
  success: boolean;
  message: string;
  details?: string;
  timestamp: string;
}

export function ProductSync() {
  const [syncing, setSyncing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [syncResults, setSyncResults] = useState<SyncResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleSyncProducts = async () => {
    try {
      setSyncing(true);
      setProgress(0);
      setError(null);
      setSyncResults([]);

      toast.loading('开始同步商品...', { id: 'sync-products' });

      // 模拟进度更新
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 500);

      const response = await frontendApi.post('/api/products/sync', {
        sync_type: 'full', // 或者 'incremental'
      });

      clearInterval(progressInterval);
      setProgress(100);

      const result: SyncResult = {
        success: true,
        message: '商品同步完成',
        details: `成功同步 ${response.data.products_saved || 0} 个商品`,
        timestamp: new Date().toLocaleString('zh-CN'),
      };

      setSyncResults([result]);
      toast.success('商品同步完成！', { id: 'sync-products' });
    } catch (err: any) {
      console.error('Product sync failed:', err);
      const errorMessage = err.response?.data?.detail || '商品同步失败';
      setError(errorMessage);

      const result: SyncResult = {
        success: false,
        message: '商品同步失败',
        details: errorMessage,
        timestamp: new Date().toLocaleString('zh-CN'),
      };

      setSyncResults([result]);
      toast.error('商品同步失败！', { id: 'sync-products' });
    } finally {
      setSyncing(false);
    }
  };

  const handleRefreshStatus = async () => {
    try {
      await frontendApi.get('/api/products/sync/status');
      // 处理状态更新
      toast.success('状态已更新');
    } catch (err: any) {
      console.error('Failed to refresh status:', err);
      toast.error('获取状态失败');
    }
  };

  const getResultIcon = (success: boolean) => {
    return success ? (
      <CheckIcon color='success' />
    ) : (
      <ErrorIcon color='error' />
    );
  };

  const getResultColor = (success: boolean) => {
    return success ? 'success' : 'error';
  };

  return (
    <Box>
      <Box
        display='flex'
        justifyContent='space-between'
        alignItems='center'
        mb={3}
      >
        <Typography variant='h4' component='h1'>
          商品同步
        </Typography>
        <Button
          variant='outlined'
          startIcon={<RefreshIcon />}
          onClick={handleRefreshStatus}
          disabled={syncing}
        >
          刷新状态
        </Button>
      </Box>

      <Box display='flex' gap={3}>
        {/* 同步控制面板 */}
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography variant='h6' gutterBottom>
              同步操作
            </Typography>
            <Typography variant='body2' color='text.secondary' paragraph>
              从 Shopify 同步商品信息到系统，包括商品详情、变体和图片。
            </Typography>

            {error && (
              <Alert severity='error' sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            <Box mb={3}>
              <Button
                variant='contained'
                startIcon={<SyncIcon />}
                onClick={handleSyncProducts}
                disabled={syncing}
                fullWidth
                size='large'
              >
                {syncing ? '同步中...' : '开始同步商品'}
              </Button>
            </Box>

            {syncing && (
              <Box>
                <Box display='flex' justifyContent='space-between' mb={1}>
                  <Typography variant='body2' color='text.secondary'>
                    同步进度
                  </Typography>
                  <Typography variant='body2' color='text.secondary'>
                    {progress}%
                  </Typography>
                </Box>
                <LinearProgress variant='determinate' value={progress} />
              </Box>
            )}
          </CardContent>
        </Card>

        {/* 同步历史 */}
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography variant='h6' gutterBottom>
              同步历史
            </Typography>
            <Typography variant='body2' color='text.secondary' paragraph>
              查看最近的同步操作结果。
            </Typography>

            {syncResults.length === 0 ? (
              <Paper
                variant='outlined'
                sx={{
                  p: 3,
                  textAlign: 'center',
                  bgcolor: 'grey.50',
                }}
              >
                <Typography variant='body2' color='text.secondary'>
                  暂无同步记录
                </Typography>
              </Paper>
            ) : (
              <List>
                {syncResults.map((result, index) => (
                  <React.Fragment key={index}>
                    <ListItem>
                      <ListItemIcon>
                        {getResultIcon(result.success)}
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box display='flex' alignItems='center' gap={1}>
                            <Typography variant='body2' fontWeight='medium'>
                              {result.message}
                            </Typography>
                            <Chip
                              label={result.success ? '成功' : '失败'}
                              color={getResultColor(result.success) as any}
                              size='small'
                            />
                          </Box>
                        }
                        secondary={
                          <Box>
                            <Typography
                              variant='caption'
                              color='text.secondary'
                            >
                              {result.timestamp}
                            </Typography>
                            {result.details && (
                              <Typography variant='caption' display='block'>
                                {result.details}
                              </Typography>
                            )}
                          </Box>
                        }
                      />
                    </ListItem>
                    {index < syncResults.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            )}
          </CardContent>
        </Card>
      </Box>

      {/* 同步说明 */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant='h6' gutterBottom>
            同步说明
          </Typography>
          <Box component='ul' sx={{ pl: 2, m: 0 }}>
            <Typography component='li' variant='body2' paragraph>
              全量同步：同步所有 Shopify 商品信息
            </Typography>
            <Typography component='li' variant='body2' paragraph>
              增量同步：只同步最近更新的商品
            </Typography>
            <Typography component='li' variant='body2' paragraph>
              同步内容包括：商品标题、描述、价格、变体、图片等
            </Typography>
            <Typography component='li' variant='body2' paragraph>
              同步过程中请勿关闭页面，以免中断操作
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
