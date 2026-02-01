'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Switch,
  FormControlLabel,
  TextField,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Stack,
  Divider,
  Grid,
  Paper,
  Tabs,
  Tab,
  Badge,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  PlayArrow as PlayIcon,
  Settings as SettingsIcon,
  Info as InfoIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
  Category as CategoryIcon,
} from '@mui/icons-material';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';
import toast from 'react-hot-toast';

// 类型定义
interface AutomationStep {
  id: number;
  step_key: string;
  name: string;
  description?: string;
  category: string;
  required_external_systems?: string[];
  celery_task_name?: string;
  default_schedule?: string;
  default_enabled: boolean;
  is_manual_only: boolean;
  created_at?: string;
  updated_at?: string;
}

interface TenantAutomationConfig {
  id: number;
  tenant_id: number;
  step_key: string;
  is_enabled: boolean;
  schedule?: string;
  schedule_seconds?: number;
  task_params?: Record<string, any>;
  external_system_types?: string[];
  external_system_ids?: string[];
  is_active: boolean;
  last_run_at?: string;
  last_run_status?: string;
  last_run_error?: string;
  created_at?: string;
  updated_at?: string;
}

interface AutomationManualButton {
  id: number;
  step_key: string;
  button_key: string;
  button_label: string;
  button_action: string;
  http_method: string;
  is_recommended: boolean;
  is_deprecated: boolean;
  deprecated_reason?: string;
  page_path?: string;
  order: number;
}

interface AutomationStepWithConfig extends AutomationStep {
  tenant_config?: TenantAutomationConfig;
  manual_buttons: AutomationManualButton[];
}

const AutomationPage: React.FC = () => {
  const [steps, setSteps] = useState<AutomationStepWithConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedStep, setSelectedStep] = useState<AutomationStepWithConfig | null>(null);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [triggerDialogOpen, setTriggerDialogOpen] = useState(false);
  const [updating, setUpdating] = useState<string | null>(null);
  const [triggering, setTriggering] = useState<string | null>(null);

  // 获取步骤列表
  const fetchSteps = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      frontendLogger.info('🔍 开始获取自动化步骤列表');

      const response = await frontendApi.get('/api/automation/steps-with-configs', {
        params: selectedCategory !== 'all' ? { category: selectedCategory } : {},
      });

      setSteps(response.data);
      frontendLogger.info('✅ 获取自动化步骤列表成功', { count: response.data.length });
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || '获取自动化步骤列表失败';
      setError(errorMessage);
      frontendLogger.error('❌ 获取自动化步骤列表失败', { error: errorMessage });
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [selectedCategory]);

  useEffect(() => {
    fetchSteps();
  }, [fetchSteps]);

  // 更新配置
  const handleUpdateConfig = async (stepKey: string, updates: Partial<TenantAutomationConfig>) => {
    try {
      setUpdating(stepKey);
      frontendLogger.info('🔄 开始更新自动化配置', { stepKey, updates });

      const response = await frontendApi.put(`/api/automation/configs/${stepKey}`, updates);

      // 更新本地状态
      setSteps(prevSteps =>
        prevSteps.map(step =>
          step.step_key === stepKey
            ? { ...step, tenant_config: response.data }
            : step
        )
      );

      frontendLogger.info('✅ 更新自动化配置成功', { stepKey });
      toast.success('配置更新成功');
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || '更新配置失败';
      frontendLogger.error('❌ 更新自动化配置失败', { error: errorMessage });
      toast.error(errorMessage);
    } finally {
      setUpdating(null);
    }
  };

  // 切换自动化开关
  const handleToggleAutomation = async (step: AutomationStepWithConfig) => {
    const newEnabled = !step.tenant_config?.is_enabled;
    await handleUpdateConfig(step.step_key, { is_enabled: newEnabled });
  };

  // 手动触发
  const handleTrigger = async (stepKey: string) => {
    try {
      setTriggering(stepKey);
      frontendLogger.info('🚀 开始手动触发自动化步骤', { stepKey });

      const response = await frontendApi.post(`/api/automation/configs/${stepKey}/trigger`, {});

      frontendLogger.info('✅ 手动触发成功', { stepKey, taskId: response.data.task_id });
      toast.success(`任务已触发，任务ID: ${response.data.task_id}`);
      setTriggerDialogOpen(false);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || '触发失败';
      frontendLogger.error('❌ 手动触发失败', { error: errorMessage });
      toast.error(errorMessage);
    } finally {
      setTriggering(null);
    }
  };

  // 格式化计划显示
  const formatSchedule = (schedule?: string, scheduleSeconds?: number) => {
    if (scheduleSeconds) {
      const minutes = scheduleSeconds / 60;
      return `每 ${minutes} 分钟`;
    }
    if (schedule) {
      // 解析cron表达式
      if (schedule.startsWith('*/')) {
        const minutes = schedule.split('*/')[1].split(' ')[0];
        return `每 ${minutes} 分钟`;
      }
      return schedule;
    }
    return '未配置';
  };

  // 获取状态颜色
  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'success':
        return 'success';
      case 'failed':
        return 'error';
      case 'running':
        return 'info';
      default:
        return 'default';
    }
  };

  // 获取类别标签
  const getCategoryLabel = (category: string) => {
    const labels: Record<string, string> = {
      order_sync: '订单同步',
      order_processing: '订单处理',
      status_sync: '状态同步',
    };
    return labels[category] || category;
  };

  // 分类统计
  const categoryCounts = steps.reduce((acc, step) => {
    acc[step.category] = (acc[step.category] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const categories = ['all', 'order_sync', 'order_processing', 'status_sync'];

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Box sx={{ maxWidth: '1400px', mx: 'auto', p: 3 }}>
          {/* 页面标题 */}
          <Box sx={{ mb: 4 }}>
            <Typography variant='h4' component='h1' gutterBottom>
              自动化管理
            </Typography>
            <Typography variant='body1' color='text.secondary'>
              管理订单处理流程的自动化步骤，包括同步、处理和状态更新
            </Typography>
          </Box>

          {/* 错误提示 */}
          {error && (
            <Alert severity='error' sx={{ mb: 3 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          {/* 操作栏 */}
          <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Tabs
              value={selectedCategory}
              onChange={(_, newValue) => setSelectedCategory(newValue)}
              sx={{ minHeight: 'auto' }}
            >
              <Tab
                label={
                  <Badge badgeContent={steps.length} color='primary'>
                    全部
                  </Badge>
                }
                value='all'
              />
              <Tab
                label={
                  <Badge badgeContent={categoryCounts['order_sync'] || 0} color='primary'>
                    订单同步
                  </Badge>
                }
                value='order_sync'
              />
              <Tab
                label={
                  <Badge badgeContent={categoryCounts['order_processing'] || 0} color='primary'>
                    订单处理
                  </Badge>
                }
                value='order_processing'
              />
              <Tab
                label={
                  <Badge badgeContent={categoryCounts['status_sync'] || 0} color='primary'>
                    状态同步
                  </Badge>
                }
                value='status_sync'
              />
            </Tabs>

            <Button
              variant='outlined'
              startIcon={<RefreshIcon />}
              onClick={fetchSteps}
              disabled={loading}
            >
              刷新
            </Button>
          </Box>

          {/* 加载状态 */}
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
              <CircularProgress />
            </Box>
          ) : (
            /* 步骤列表 */
            <Grid container spacing={3}>
              {steps.map(step => (
                <Grid item xs={12} md={6} lg={4} key={step.id}>
                  <Card
                    sx={{
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      transition: 'box-shadow 0.3s',
                      '&:hover': {
                        boxShadow: 4,
                      },
                    }}
                  >
                    <CardContent sx={{ flexGrow: 1 }}>
                      {/* 步骤头部 */}
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', mb: 2 }}>
                        <Box sx={{ flex: 1 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <CategoryIcon color='primary' fontSize='small' />
                            <Chip
                              label={getCategoryLabel(step.category)}
                              size='small'
                              color='primary'
                              variant='outlined'
                            />
                          </Box>
                          <Typography variant='h6' component='h3' gutterBottom>
                            {step.name}
                          </Typography>
                          {step.description && (
                            <Typography variant='body2' color='text.secondary' sx={{ mb: 2 }}>
                              {step.description}
                            </Typography>
                          )}
                        </Box>
                      </Box>

                      {/* 所需外部系统 */}
                      {step.required_external_systems && step.required_external_systems.length > 0 && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant='caption' color='text.secondary' sx={{ display: 'block', mb: 0.5 }}>
                            所需外部系统:
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                            {step.required_external_systems.map(system => (
                              <Chip key={system} label={system} size='small' variant='outlined' />
                            ))}
                          </Box>
                        </Box>
                      )}

                      <Divider sx={{ my: 2 }} />

                      {/* 自动化配置 */}
                      <Box sx={{ mb: 2 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                          <Typography variant='subtitle2'>自动化</Typography>
                          <FormControlLabel
                            control={
                              <Switch
                                checked={step.tenant_config?.is_enabled || false}
                                onChange={() => handleToggleAutomation(step)}
                                disabled={step.is_manual_only || updating === step.step_key}
                                size='small'
                              />
                            }
                            label={step.tenant_config?.is_enabled ? '已启用' : '未启用'}
                            sx={{ m: 0 }}
                          />
                        </Box>

                        {step.tenant_config?.is_enabled && (
                          <Box sx={{ pl: 4 }}>
                            <Typography variant='caption' color='text.secondary' sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <ScheduleIcon fontSize='inherit' />
                              {formatSchedule(step.tenant_config.schedule, step.tenant_config.schedule_seconds)}
                            </Typography>
                          </Box>
                        )}

                        {/* 最后运行状态 */}
                        {step.tenant_config?.last_run_at && (
                          <Box sx={{ mt: 1, pl: 4 }}>
                            <Typography variant='caption' color='text.secondary' sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              {step.tenant_config.last_run_status === 'success' && <CheckCircleIcon fontSize='inherit' color='success' />}
                              {step.tenant_config.last_run_status === 'failed' && <ErrorIcon fontSize='inherit' color='error' />}
                              {step.tenant_config.last_run_status === 'running' && <CircularProgress size={12} />}
                              最后运行: {new Date(step.tenant_config.last_run_at).toLocaleString('zh-CN')}
                            </Typography>
                          </Box>
                        )}
                      </Box>

                      {/* 操作按钮 */}
                      <Box sx={{ display: 'flex', gap: 1, mt: 'auto' }}>
                        {!step.is_manual_only && (
                          <Tooltip title='手动触发'>
                            <IconButton
                              size='small'
                              color='primary'
                              onClick={() => {
                                setSelectedStep(step);
                                setTriggerDialogOpen(true);
                              }}
                              disabled={triggering === step.step_key}
                            >
                              {triggering === step.step_key ? (
                                <CircularProgress size={20} />
                              ) : (
                                <PlayIcon />
                              )}
                            </IconButton>
                          </Tooltip>
                        )}
                        <Tooltip title='配置'>
                          <IconButton
                            size='small'
                            onClick={() => {
                              setSelectedStep(step);
                              setConfigDialogOpen(true);
                            }}
                          >
                            <SettingsIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title='详情'>
                          <IconButton
                            size='small'
                            onClick={() => {
                              setSelectedStep(step);
                              // 可以打开详情对话框
                            }}
                          >
                            <InfoIcon />
                          </IconButton>
                        </Tooltip>
                      </Box>

                      {/* 手动按钮列表 */}
                      {step.manual_buttons && step.manual_buttons.length > 0 && (
                        <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                          <Typography variant='caption' color='text.secondary' sx={{ display: 'block', mb: 1 }}>
                            手动操作:
                          </Typography>
                          <Stack spacing={0.5}>
                            {step.manual_buttons
                              .filter(btn => !btn.is_deprecated)
                              .sort((a, b) => a.order - b.order)
                              .map(button => (
                                <Chip
                                  key={button.id}
                                  label={button.button_label}
                                  size='small'
                                  color={button.is_recommended ? 'primary' : 'default'}
                                  variant={button.is_recommended ? 'filled' : 'outlined'}
                                  sx={{ fontSize: '0.75rem' }}
                                />
                              ))}
                          </Stack>
                        </Box>
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}

          {/* 配置对话框 */}
          <Dialog
            open={configDialogOpen}
            onClose={() => setConfigDialogOpen(false)}
            maxWidth='sm'
            fullWidth
          >
            <DialogTitle>配置自动化步骤</DialogTitle>
            <DialogContent>
              {selectedStep && (
                <Box sx={{ pt: 2 }}>
                  <Typography variant='h6' gutterBottom>
                    {selectedStep.name}
                  </Typography>
                  {selectedStep.description && (
                    <Typography variant='body2' color='text.secondary' sx={{ mb: 3 }}>
                      {selectedStep.description}
                    </Typography>
                  )}

                  <Stack spacing={3}>
                    {/* 启用开关 */}
                    <FormControlLabel
                      control={
                        <Switch
                          checked={selectedStep.tenant_config?.is_enabled || false}
                          onChange={e =>
                            handleUpdateConfig(selectedStep.step_key, {
                              is_enabled: e.target.checked,
                            })
                          }
                          disabled={selectedStep.is_manual_only || updating === selectedStep.step_key}
                        />
                      }
                      label='启用自动化'
                    />

                    {selectedStep.tenant_config?.is_enabled && !selectedStep.is_manual_only && (
                      <>
                        {/* 计划配置 */}
                        <TextField
                          label='Cron表达式'
                          value={selectedStep.tenant_config?.schedule || selectedStep.default_schedule || ''}
                          onChange={e =>
                            handleUpdateConfig(selectedStep.step_key, {
                              schedule: e.target.value,
                            })
                          }
                          placeholder='*/30 * * * *'
                          helperText='例如: */30 * * * * 表示每30分钟执行一次'
                          fullWidth
                          disabled={updating === selectedStep.step_key}
                        />

                        {/* 或使用秒数 */}
                        <TextField
                          label='计划秒数（可选）'
                          type='number'
                          value={selectedStep.tenant_config?.schedule_seconds || ''}
                          onChange={e =>
                            handleUpdateConfig(selectedStep.step_key, {
                              schedule_seconds: e.target.value ? parseInt(e.target.value) : null,
                            })
                          }
                          placeholder='1800 (30分钟)'
                          helperText='如果设置了秒数，将优先使用秒数而不是Cron表达式'
                          fullWidth
                          disabled={updating === selectedStep.step_key}
                        />
                      </>
                    )}

                    {/* 最后运行信息 */}
                    {selectedStep.tenant_config?.last_run_at && (
                      <Box>
                        <Typography variant='subtitle2' gutterBottom>
                          最后运行信息
                        </Typography>
                        <Typography variant='body2' color='text.secondary'>
                          时间: {new Date(selectedStep.tenant_config.last_run_at).toLocaleString('zh-CN')}
                        </Typography>
                        <Typography variant='body2' color='text.secondary'>
                          状态:{' '}
                          <Chip
                            label={selectedStep.tenant_config.last_run_status || '未知'}
                            size='small'
                            color={getStatusColor(selectedStep.tenant_config.last_run_status) as any}
                          />
                        </Typography>
                        {selectedStep.tenant_config.last_run_error && (
                          <Alert severity='error' sx={{ mt: 1 }}>
                            {selectedStep.tenant_config.last_run_error}
                          </Alert>
                        )}
                      </Box>
                    )}
                  </Stack>
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setConfigDialogOpen(false)}>关闭</Button>
            </DialogActions>
          </Dialog>

          {/* 触发对话框 */}
          <Dialog
            open={triggerDialogOpen}
            onClose={() => setTriggerDialogOpen(false)}
            maxWidth='sm'
            fullWidth
          >
            <DialogTitle>手动触发自动化步骤</DialogTitle>
            <DialogContent>
              {selectedStep && (
                <Box sx={{ pt: 2 }}>
                  <Typography variant='body1' gutterBottom>
                    确定要手动触发以下步骤吗？
                  </Typography>
                  <Typography variant='h6' color='primary' sx={{ mt: 2, mb: 1 }}>
                    {selectedStep.name}
                  </Typography>
                  {selectedStep.description && (
                    <Typography variant='body2' color='text.secondary'>
                      {selectedStep.description}
                    </Typography>
                  )}
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setTriggerDialogOpen(false)}>取消</Button>
              <Button
                variant='contained'
                onClick={() => selectedStep && handleTrigger(selectedStep.step_key)}
                disabled={triggering === selectedStep?.step_key}
                startIcon={triggering === selectedStep?.step_key ? <CircularProgress size={20} /> : <PlayIcon />}
              >
                {triggering === selectedStep?.step_key ? '触发中...' : '触发'}
              </Button>
            </DialogActions>
          </Dialog>
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
};

export default AutomationPage;















