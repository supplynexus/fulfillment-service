/**
 * 错误监控仪表板组件
 * 
 * 显示错误统计、趋势和健康状态
 */

import React, { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  LinearProgress,
  Alert,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
} from '@mui/material'
import {
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
  Clear as ClearIcon,
  Health as HealthIcon,
} from '@mui/icons-material'

interface ErrorStats {
  total_errors: number
  error_types: Record<string, { count: number; severities: Record<string, number> }>
  recent_errors: Array<{
    error_type: string
    severity: string
    message: string
    timestamp: string
    request_id?: string
  }>
  error_trends: {
    hourly: Array<{ time: string; count: number }>
    daily: Array<{ time: string; count: number }>
    weekly: Array<{ time: string; count: number }>
  }
}

interface ErrorHealth {
  health_score: number
  health_status: 'healthy' | 'warning' | 'critical'
  total_errors: number
  critical_errors: number
  last_updated: string
}

export function ErrorDashboard() {
  const [errorStats, setErrorStats] = useState<ErrorStats | null>(null)
  const [errorHealth, setErrorHealth] = useState<ErrorHealth | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadErrorStats = async () => {
    try {
      setLoading(true)
      setError(null)

      const [statsResponse, healthResponse] = await Promise.all([
        fetch('/api/errors/stats', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
        }),
        fetch('/api/errors/health', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
        }),
      ])

      if (!statsResponse.ok || !healthResponse.ok) {
        throw new Error('获取错误统计失败')
      }

      const [stats, health] = await Promise.all([
        statsResponse.json(),
        healthResponse.json(),
      ])

      setErrorStats(stats)
      setErrorHealth(health)
    } catch (err: any) {
      setError(err.message || '加载错误统计失败')
    } finally {
      setLoading(false)
    }
  }

  const clearErrorQueue = async () => {
    try {
      const response = await fetch('/api/errors/clear', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      })

      if (!response.ok) {
        throw new Error('清理错误队列失败')
      }

      // 重新加载数据
      await loadErrorStats()
    } catch (err: any) {
      setError(err.message || '清理错误队列失败')
    }
  }

  useEffect(() => {
    loadErrorStats()
  }, [])

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'error'
      case 'high':
        return 'error'
      case 'medium':
        return 'warning'
      case 'low':
        return 'info'
      default:
        return 'default'
    }
  }

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success'
      case 'warning':
        return 'warning'
      case 'critical':
        return 'error'
      default:
        return 'default'
    }
  }

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          错误监控
        </Typography>
        <LinearProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        <Button variant="contained" onClick={loadErrorStats}>
          重试
        </Button>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6">
          错误监控
        </Typography>
        <Box>
          <Tooltip title="刷新数据">
            <IconButton onClick={loadErrorStats}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="清理错误队列">
            <IconButton onClick={clearErrorQueue}>
              <ClearIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* 健康状态卡片 */}
        {errorHealth && (
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <HealthIcon sx={{ mr: 1 }} />
                  <Typography variant="h6">
                    系统健康状态
                  </Typography>
                </Box>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="h4" color={`${getHealthColor(errorHealth.health_status)}.main`}>
                    {errorHealth.health_score}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    健康分数
                  </Typography>
                </Box>
                <Chip
                  label={errorHealth.health_status.toUpperCase()}
                  color={getHealthColor(errorHealth.health_status) as any}
                  size="small"
                />
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2">
                    总错误数: {errorHealth.total_errors}
                  </Typography>
                  <Typography variant="body2">
                    严重错误: {errorHealth.critical_errors}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* 错误统计卡片 */}
        {errorStats && (
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  错误统计
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" color="error.main">
                        {errorStats.total_errors}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        总错误数
                      </Typography>
                    </Box>
                  </Grid>
                  {Object.entries(errorStats.error_types).map(([type, data]) => (
                    <Grid item xs={6} sm={3} key={type}>
                      <Box sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="warning.main">
                          {data.count}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {type.replace('_', ' ')}
                        </Typography>
                      </Box>
                    </Grid>
                  ))}
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* 最近错误表格 */}
        {errorStats && errorStats.recent_errors.length > 0 && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  最近错误
                </Typography>
                <TableContainer component={Paper}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>类型</TableCell>
                        <TableCell>严重程度</TableCell>
                        <TableCell>消息</TableCell>
                        <TableCell>时间</TableCell>
                        <TableCell>请求ID</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {errorStats.recent_errors.map((error, index) => (
                        <TableRow key={index}>
                          <TableCell>
                            <Chip
                              label={error.error_type}
                              size="small"
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={error.severity}
                              color={getSeverityColor(error.severity) as any}
                              size="small"
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" noWrap>
                              {error.message}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {new Date(error.timestamp).toLocaleString()}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" fontFamily="monospace">
                              {error.request_id || '-'}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* 空状态 */}
        {errorStats && errorStats.recent_errors.length === 0 && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <InfoIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary">
                    暂无错误记录
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    系统运行正常，没有发现错误
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  )
}
