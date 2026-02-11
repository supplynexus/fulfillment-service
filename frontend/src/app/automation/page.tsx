'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
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
  Paper,
  Tabs,
  Tab,
  Badge,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  PlayArrow as PlayIcon,
  Settings as SettingsIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
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

/** 配置弹窗内的草稿，仅点「保存」时提交 */
interface ConfigDraft {
  is_enabled: boolean;
  schedule: string;
  schedule_seconds: number | '';
}

/** 校验 5 段 cron（分 时 日 月 周），不合法返回错误文案 */
function validateCron(schedule: string): string | null {
  const t = schedule.trim();
  if (!t) return null;
  const parts = t.split(/\s+/);
  if (parts.length !== 5) {
    return 'Cron 应为 5 段：分 时 日 月 周，用空格分隔，例如：*/30 * * * *';
  }
  const partRe = /^(\*|\d+|\*\/\d+|\d+-\d+|\d+(\,\d+)*)$/;
  for (let i = 0; i < 5; i++) {
    if (!partRe.test(parts[i].trim())) {
      return `第 ${i + 1} 段格式不正确，支持：* 、数字、*/n、n-m、n,m`;
    }
  }
  return null;
}

/** 步骤的一行说明（更清晰、面向操作结果） */
const STEP_SUMMARY: Record<string, string> = {
  sync_external_orders: '从 Shopify 拉取订单到本地 shopify_orders 表，供后续同步到核心订单使用',
  sync_to_core_orders: '把 shopify_orders 里未同步的订单写入核心 orders 表，并做地址验证',
  create_scm_orders: '把核心订单中的商品生成 SCM 订单，用于后续发 Printify 等',
  create_printify_orders_from_scm: '根据 SCM 订单在 Printify 侧批量创建生产订单',
  sync_printify_orders_to_local: '从 Printify API 拉取订单到本地 printify_orders 表',
  auto_create_scm_from_unbound_printify_orders: '对未绑定 SCM 的 Printify 订单自动创建 SCM 并绑定（补全 Printify→SCM）',
  sync_fulfillment_status: '把 printify_orders 的发货/物流状态回写到 SCM 订单',
  sync_to_external_fulfillment: '把 SCM 的发货状态同步回 Shopify 履约信息',
  sync_shopify_fulfillment_to_local: '从 Shopify API 拉取履约/物流信息到 shopify_orders',
  sync_shopify_local_fulfillment_to_core: '把 shopify_orders 的物流信息写入核心 orders 表',
};

function getStepSummary(step: AutomationStep): string {
  return STEP_SUMMARY[step.step_key] || step.description || step.name;
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
  /** 配置弹窗草稿，打开时从 selectedStep 初始化，仅保存时提交 */
  const [configDraft, setConfigDraft] = useState<ConfigDraft | null>(null);
  const [configDraftError, setConfigDraftError] = useState<string | null>(null);

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

  // 打开配置弹窗时，用当前步骤的配置初始化草稿
  useEffect(() => {
    if (configDialogOpen && selectedStep) {
      const c = selectedStep.tenant_config;
      setConfigDraft({
        is_enabled: c?.is_enabled ?? false,
        schedule: c?.schedule ?? selectedStep.default_schedule ?? '',
        schedule_seconds: c?.schedule_seconds ?? '',
      });
      setConfigDraftError(null);
    } else {
      setConfigDraft(null);
      setConfigDraftError(null);
    }
  }, [configDialogOpen, selectedStep]);

  // 更新配置
  const handleUpdateConfig = async (stepKey: string, updates: Partial<TenantAutomationConfig>) => {
    try {
      setUpdating(stepKey);
      frontendLogger.info('🔄 开始更新自动化配置', { stepKey, updates });

      const response = await frontendApi.put(`/api/automation/configs/${stepKey}`, updates);

      // 更新本地状态（列表 + 若当前打开的是该步骤则同步弹窗）
      const updatedConfig = response.data;
      setSteps(prevSteps =>
        prevSteps.map(step =>
          step.step_key === stepKey
            ? { ...step, tenant_config: updatedConfig }
            : step
        )
      );
      if (selectedStep?.step_key === stepKey) {
        setSelectedStep(prev => (prev ? { ...prev, tenant_config: updatedConfig } : null));
      }

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

  // 切换自动化开关（仅卡片上的开关，弹窗内用草稿+保存）
  const handleToggleAutomation = async (step: AutomationStepWithConfig) => {
    const newEnabled = !step.tenant_config?.is_enabled;
    await handleUpdateConfig(step.step_key, { is_enabled: newEnabled });
  };

  // 配置弹窗：保存草稿（校验 cron 后提交）
  const handleSaveConfigDraft = async () => {
    if (!selectedStep || !configDraft) return;
    setConfigDraftError(null);
    const useScheduleSeconds = configDraft.schedule_seconds !== '' && configDraft.schedule_seconds !== null;
    const scheduleStr = configDraft.schedule.trim();
    if (!useScheduleSeconds && scheduleStr) {
      const err = validateCron(scheduleStr);
      if (err) {
        setConfigDraftError(err);
        return;
      }
    }
    if (useScheduleSeconds) {
      const n = Number(configDraft.schedule_seconds);
      if (!Number.isInteger(n) || n < 1) {
        setConfigDraftError('计划秒数请填写正整数');
        return;
      }
    }
    try {
      await handleUpdateConfig(selectedStep.step_key, {
        is_enabled: configDraft.is_enabled,
        schedule: scheduleStr || undefined,
        schedule_seconds: useScheduleSeconds ? Number(configDraft.schedule_seconds) : undefined,
      });
      setConfigDialogOpen(false);
    } catch {
      // handleUpdateConfig 内部已 toast
    }
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
      product_sync: '商品同步',
    };
    return labels[category] || category;
  };

  // 分类统计
  const categoryCounts = steps.reduce((acc, step) => {
    acc[step.category] = (acc[step.category] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const categories = ['all', 'order_sync', 'product_sync', 'order_processing', 'status_sync'];

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
                  <Badge badgeContent={categoryCounts['product_sync'] || 0} color='primary'>
                    商品同步
                  </Badge>
                }
                value='product_sync'
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
            /* 简洁列表：一行一项，左侧名称+说明，右侧定时/配置/开关 */
            <Paper variant='outlined' sx={{ overflow: 'hidden' }}>
              {steps.map((step, index) => (
                <Box
                  key={step.id}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 2,
                    px: 2,
                    py: 1.5,
                    borderBottom: index < steps.length - 1 ? '1px solid' : 'none',
                    borderColor: 'divider',
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                >
                  {/* 左侧：名称 + 一行说明 + 分类 */}
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.25 }}>
                      <Typography variant='subtitle1' fontWeight={600}>
                        {step.name}
                      </Typography>
                      <Chip
                        label={getCategoryLabel(step.category)}
                        size='small'
                        variant='outlined'
                        sx={{ height: 20, fontSize: '0.7rem' }}
                      />
                      {step.required_external_systems && step.required_external_systems.length > 0 && (
                        <Typography component='span' variant='caption' color='text.secondary'>
                          ({step.required_external_systems.join(', ')})
                        </Typography>
                      )}
                    </Box>
                    <Typography variant='body2' color='text.secondary' sx={{ lineHeight: 1.4 }}>
                      {getStepSummary(step)}
                    </Typography>
                    {step.tenant_config?.last_run_at && (
                      <Typography variant='caption' color='text.secondary' sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                        {step.tenant_config.last_run_status === 'success' && <CheckCircleIcon fontSize='inherit' color='success' sx={{ fontSize: 14 }} />}
                        {step.tenant_config.last_run_status === 'failed' && <ErrorIcon fontSize='inherit' color='error' sx={{ fontSize: 14 }} />}
                        最后运行: {new Date(step.tenant_config.last_run_at).toLocaleString('zh-CN')}
                      </Typography>
                    )}
                  </Box>

                  {/* 右侧：定时文案 + 配置 + 运行 + 开关 */}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexShrink: 0 }}>
                    {!step.is_manual_only && (
                      <Typography variant='caption' color='text.secondary' sx={{ minWidth: 64, textAlign: 'right' }}>
                        {step.tenant_config?.is_enabled
                          ? formatSchedule(step.tenant_config.schedule, step.tenant_config.schedule_seconds)
                          : '—'}
                      </Typography>
                    )}
                    <Tooltip title='配置定时（Cron）'>
                      <Button
                        size='small'
                        variant='outlined'
                        startIcon={<SettingsIcon />}
                        onClick={() => {
                          setSelectedStep(step);
                          setConfigDialogOpen(true);
                        }}
                      >
                        配置
                      </Button>
                    </Tooltip>
                    {!step.is_manual_only && (
                      <Tooltip title='立即运行一次'>
                        <IconButton
                          size='small'
                          color='primary'
                          onClick={() => {
                            setSelectedStep(step);
                            setTriggerDialogOpen(true);
                          }}
                          disabled={triggering === step.step_key}
                        >
                          {triggering === step.step_key ? <CircularProgress size={20} /> : <PlayIcon />}
                        </IconButton>
                      </Tooltip>
                    )}
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
                </Box>
              ))}
            </Paper>
          )}

          {/* 配置对话框：草稿编辑，点「保存」才提交；cron 不合法会报错 */}
          <Dialog
            open={configDialogOpen}
            onClose={() => setConfigDialogOpen(false)}
            maxWidth='sm'
            fullWidth
          >
            <DialogTitle>配置自动化步骤</DialogTitle>
            <DialogContent>
              {selectedStep && configDraft && (
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
                    {/* 启用开关（草稿） */}
                    <FormControlLabel
                      control={
                        <Switch
                          checked={configDraft.is_enabled}
                          onChange={e =>
                            setConfigDraft(prev => (prev ? { ...prev, is_enabled: e.target.checked } : prev))
                          }
                          disabled={selectedStep.is_manual_only}
                        />
                      }
                      label='启用自动化'
                    />

                    {configDraft.is_enabled && !selectedStep.is_manual_only && (
                      <>
                        {/* Cron（草稿）；未填秒数时保存会校验 */}
                        <TextField
                          label='Cron表达式'
                          value={configDraft.schedule}
                          onChange={e => {
                            setConfigDraft(prev => (prev ? { ...prev, schedule: e.target.value } : prev));
                            if (configDraftError) setConfigDraftError(null);
                          }}
                          placeholder='*/30 * * * *'
                          helperText='例如: */30 * * * * 表示每30分钟，* * * * * 表示每分钟'
                          fullWidth
                          error={!!configDraftError}
                        />
                        {configDraftError && (
                          <Alert severity='error' onClose={() => setConfigDraftError(null)}>
                            {configDraftError}
                          </Alert>
                        )}

                        {/* 计划秒数（可选）；填了则优先用秒数 */}
                        <TextField
                          label='计划秒数（可选）'
                          type='number'
                          value={configDraft.schedule_seconds === '' ? '' : configDraft.schedule_seconds}
                          onChange={e => {
                            const v = e.target.value;
                            setConfigDraft(prev =>
                              prev ? { ...prev, schedule_seconds: v === '' ? '' : parseInt(v, 10) || 0 } : prev
                            );
                            if (configDraftError) setConfigDraftError(null);
                          }}
                          placeholder='60=每分钟，1800=每30分钟'
                          helperText='若填写，将优先按秒数执行，不再使用 Cron'
                          fullWidth
                          inputProps={{ min: 1 }}
                        />
                      </>
                    )}

                    {/* 最后运行信息（只读，来自已保存配置） */}
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
              <Button
                variant='contained'
                onClick={handleSaveConfigDraft}
                disabled={!configDraft || updating === selectedStep?.step_key}
                startIcon={updating === selectedStep?.step_key ? <CircularProgress size={20} /> : null}
              >
                {updating === selectedStep?.step_key ? '保存中...' : '保存'}
              </Button>
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















