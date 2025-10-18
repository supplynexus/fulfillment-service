'use client';

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Divider,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Card,
  CardContent,
  CardHeader,
  CircularProgress,
  Stepper,
  Step,
  StepLabel,
  StepContent,
} from '@mui/material';
import {
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Category as CategoryIcon,
  Dimensions as DimensionsIcon,
  Transform as TransformIcon,
} from '@mui/icons-material';

interface Product {
  id: string;
  name: string;
  code: string;
  currentCategoryId: string;
  currentCategoryName: string;
  targetCategoryId: string;
  targetCategoryName: string;
}

interface Dimension {
  id: string;
  dimensionCode: string;
  dimensionName: string;
  dimensionType: 'select' | 'text' | 'number' | 'boolean';
  isRequired: boolean;
  isOverridable: boolean;
}

interface IncompatibleDimension {
  dimension: Dimension;
  reason: 'missing' | 'incompatible_type' | 'not_overridable';
  currentValue?: string;
  suggestedAction: 'migrate_to_attribute' | 'remove' | 'keep_as_dimension';
}

interface CategorySwitchDialogProps {
  open: boolean;
  product: Product | null;
  incompatibleDimensions: IncompatibleDimension[];
  onConfirm: (actions: Record<string, string>) => void;
  onCancel: () => void;
  loading: boolean;
}

const steps = ['分析不兼容维度', '选择处理方式', '确认更改'];

export default function CategorySwitchDialog({
  open,
  product,
  incompatibleDimensions,
  onConfirm,
  onCancel,
  loading,
}: CategorySwitchDialogProps) {
  const [activeStep, setActiveStep] = useState(0);
  const [dimensionActions, setDimensionActions] = useState<
    Record<string, string>
  >({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && incompatibleDimensions.length > 0) {
      // 初始化默认处理方式
      const defaultActions: Record<string, string> = {};
      incompatibleDimensions.forEach(({ dimension, suggestedAction }) => {
        defaultActions[dimension.id] = suggestedAction;
      });
      setDimensionActions(defaultActions);
      setActiveStep(0);
      setError(null);
    }
  }, [open, incompatibleDimensions]);

  const handleNext = () => {
    if (activeStep < steps.length - 1) {
      setActiveStep(activeStep + 1);
    }
  };

  const handleBack = () => {
    if (activeStep > 0) {
      setActiveStep(activeStep - 1);
    }
  };

  const handleActionChange = (dimensionId: string, action: string) => {
    setDimensionActions(prev => ({
      ...prev,
      [dimensionId]: action,
    }));
  };

  const handleConfirm = () => {
    // 验证所有维度都有处理方式
    const unhandledDimensions = incompatibleDimensions.filter(
      ({ dimension }) => !dimensionActions[dimension.id]
    );

    if (unhandledDimensions.length > 0) {
      setError('请为所有不兼容维度选择处理方式');
      return;
    }

    onConfirm(dimensionActions);
  };

  const getReasonText = (reason: string) => {
    const reasonMap: Record<string, string> = {
      missing: '目标分类中不存在此维度',
      incompatible_type: '维度类型不兼容',
      not_overridable: '维度不可覆盖',
    };
    return reasonMap[reason] || reason;
  };

  const getReasonIcon = (reason: string) => {
    switch (reason) {
      case 'missing':
        return <ErrorIcon color='error' />;
      case 'incompatible_type':
        return <WarningIcon color='warning' />;
      case 'not_overridable':
        return <InfoIcon color='info' />;
      default:
        return <WarningIcon />;
    }
  };

  const getActionText = (action: string) => {
    const actionMap: Record<string, string> = {
      migrate_to_attribute: '迁移为产品属性',
      remove: '移除维度',
      keep_as_dimension: '保持为维度',
    };
    return actionMap[action] || action;
  };

  const getActionDescription = (action: string) => {
    const descriptionMap: Record<string, string> = {
      migrate_to_attribute: '将维度值转换为产品属性，保留现有数据',
      remove: '完全移除该维度及其所有数据',
      keep_as_dimension: '保持为独立维度，不受分类约束',
    };
    return descriptionMap[action] || '';
  };

  const getStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <Box>
            <Typography variant='h6' sx={{ mb: 2 }}>
              不兼容维度分析
            </Typography>

            <Alert severity='warning' sx={{ mb: 3 }}>
              <Typography variant='body2'>
                检测到 {incompatibleDimensions.length} 个不兼容的维度。
                这些维度在目标分类中不存在或类型不兼容，需要选择处理方式。
              </Typography>
            </Alert>

            <List>
              {incompatibleDimensions.map(
                ({ dimension, reason, currentValue }) => (
                  <ListItem
                    key={dimension.id}
                    sx={{ flexDirection: 'column', alignItems: 'flex-start' }}
                  >
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        width: '100%',
                        mb: 1,
                      }}
                    >
                      <ListItemIcon>{getReasonIcon(reason)}</ListItemIcon>
                      <ListItemText
                        primary={
                          <Box
                            sx={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: 1,
                            }}
                          >
                            <Typography variant='subtitle1'>
                              {dimension.dimensionName}
                            </Typography>
                            <Chip
                              label={dimension.dimensionType}
                              size='small'
                              color='primary'
                              variant='outlined'
                            />
                            {dimension.isRequired && (
                              <Chip
                                label='必填'
                                size='small'
                                color='error'
                                variant='outlined'
                              />
                            )}
                          </Box>
                        }
                        secondary={
                          <Box>
                            <Typography variant='body2' color='text.secondary'>
                              {getReasonText(reason)}
                            </Typography>
                            {currentValue && (
                              <Typography
                                variant='caption'
                                color='text.secondary'
                              >
                                当前值: {currentValue}
                              </Typography>
                            )}
                          </Box>
                        }
                      />
                    </Box>
                  </ListItem>
                )
              )}
            </List>
          </Box>
        );

      case 1:
        return (
          <Box>
            <Typography variant='h6' sx={{ mb: 2 }}>
              选择处理方式
            </Typography>

            <Typography variant='body2' color='text.secondary' sx={{ mb: 3 }}>
              为每个不兼容的维度选择处理方式：
            </Typography>

            {incompatibleDimensions.map(({ dimension, suggestedAction }) => (
              <Card key={dimension.id} sx={{ mb: 2 }}>
                <CardHeader
                  title={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <DimensionsIcon />
                      <Typography variant='subtitle1'>
                        {dimension.dimensionName}
                      </Typography>
                      <Chip
                        label={dimension.dimensionType}
                        size='small'
                        color='primary'
                        variant='outlined'
                      />
                    </Box>
                  }
                  subheader={`编码: ${dimension.dimensionCode}`}
                />
                <CardContent>
                  <FormControl component='fieldset'>
                    <FormLabel component='legend'>处理方式</FormLabel>
                    <RadioGroup
                      value={dimensionActions[dimension.id] || suggestedAction}
                      onChange={e =>
                        handleActionChange(dimension.id, e.target.value)
                      }
                    >
                      <FormControlLabel
                        value='migrate_to_attribute'
                        control={<Radio />}
                        label={
                          <Box>
                            <Typography variant='body2' fontWeight='medium'>
                              迁移为产品属性
                            </Typography>
                            <Typography
                              variant='caption'
                              color='text.secondary'
                            >
                              将维度值转换为产品属性，保留现有数据
                            </Typography>
                          </Box>
                        }
                      />
                      <FormControlLabel
                        value='remove'
                        control={<Radio />}
                        label={
                          <Box>
                            <Typography variant='body2' fontWeight='medium'>
                              移除维度
                            </Typography>
                            <Typography
                              variant='caption'
                              color='text.secondary'
                            >
                              完全移除该维度及其所有数据
                            </Typography>
                          </Box>
                        }
                      />
                      <FormControlLabel
                        value='keep_as_dimension'
                        control={<Radio />}
                        label={
                          <Box>
                            <Typography variant='body2' fontWeight='medium'>
                              保持为维度
                            </Typography>
                            <Typography
                              variant='caption'
                              color='text.secondary'
                            >
                              保持为独立维度，不受分类约束
                            </Typography>
                          </Box>
                        }
                      />
                    </RadioGroup>
                  </FormControl>
                </CardContent>
              </Card>
            ))}
          </Box>
        );

      case 2:
        return (
          <Box>
            <Typography variant='h6' sx={{ mb: 2 }}>
              确认更改
            </Typography>

            <Alert severity='info' sx={{ mb: 3 }}>
              <Typography variant='body2'>
                请确认以下处理方式，此操作不可撤销：
              </Typography>
            </Alert>

            <List>
              {incompatibleDimensions.map(({ dimension }) => {
                const action = dimensionActions[dimension.id];
                return (
                  <ListItem key={dimension.id}>
                    <ListItemIcon>
                      <TransformIcon />
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box
                          sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
                        >
                          <Typography variant='body1'>
                            {dimension.dimensionName}
                          </Typography>
                          <Chip
                            label={getActionText(action)}
                            color={action === 'remove' ? 'error' : 'success'}
                            size='small'
                          />
                        </Box>
                      }
                      secondary={getActionDescription(action)}
                    />
                  </ListItem>
                );
              })}
            </List>

            <Divider sx={{ my: 2 }} />

            <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
              <Typography variant='body2' color='text.secondary'>
                <strong>产品:</strong> {product?.name} ({product?.code})
              </Typography>
              <Typography variant='body2' color='text.secondary'>
                <strong>从分类:</strong> {product?.currentCategoryName}
              </Typography>
              <Typography variant='body2' color='text.secondary'>
                <strong>到分类:</strong> {product?.targetCategoryName}
              </Typography>
            </Box>
          </Box>
        );

      default:
        return null;
    }
  };

  if (!product) {
    return null;
  }

  return (
    <Dialog
      open={open}
      onClose={onCancel}
      maxWidth='md'
      fullWidth
      PaperProps={{
        sx: { minHeight: '600px' },
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CategoryIcon />
          <Typography variant='h6'>产品分类切换</Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        {/* 步骤指示器 */}
        <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
          {steps.map((label, index) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {/* 错误提示 */}
        {error && (
          <Alert severity='error' sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* 步骤内容 */}
        {getStepContent(activeStep)}
      </DialogContent>

      <DialogActions sx={{ p: 3 }}>
        <Button onClick={onCancel} disabled={loading}>
          取消
        </Button>

        {activeStep > 0 && (
          <Button onClick={handleBack} disabled={loading}>
            上一步
          </Button>
        )}

        {activeStep < steps.length - 1 ? (
          <Button variant='contained' onClick={handleNext} disabled={loading}>
            下一步
          </Button>
        ) : (
          <Button
            variant='contained'
            onClick={handleConfirm}
            disabled={loading}
            startIcon={
              loading ? <CircularProgress size={20} /> : <CheckCircleIcon />
            }
          >
            {loading ? '处理中...' : '确认切换'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
