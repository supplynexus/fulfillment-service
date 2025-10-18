'use client';

import React, { useState } from 'react';
import {
  Box,
  Button,
  Chip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  Alert,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  ContentCopy as CopyIcon,
  Download as DownloadIcon,
  Upload as UploadIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  MoreVert as MoreVertIcon,
} from '@mui/icons-material';

interface SkuBulkActionsProps {
  selectedCount: number;
  onBulkAction: (action: string) => void;
  onClearSelection: () => void;
}

export function SkuBulkActions({
  selectedCount,
  onBulkAction,
  onClearSelection,
}: SkuBulkActionsProps) {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    action: string;
    title: string;
    message: string;
  }>({
    open: false,
    action: '',
    title: '',
    message: '',
  });

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleBulkAction = (action: string) => {
    const actions = {
      edit: {
        title: '批量编辑',
        message: `确定要编辑选中的 ${selectedCount} 个 SKU 吗？`,
      },
      delete: {
        title: '批量删除',
        message: `确定要删除选中的 ${selectedCount} 个 SKU 吗？此操作不可撤销！`,
      },
      copy: {
        title: '批量复制',
        message: `确定要复制选中的 ${selectedCount} 个 SKU 吗？`,
      },
      export: {
        title: '导出数据',
        message: `确定要导出选中的 ${selectedCount} 个 SKU 数据吗？`,
      },
      import: {
        title: '导入数据',
        message: `确定要导入数据到选中的 ${selectedCount} 个 SKU 吗？`,
      },
      favorite: {
        title: '批量收藏',
        message: `确定要收藏选中的 ${selectedCount} 个 SKU 吗？`,
      },
      unfavorite: {
        title: '取消收藏',
        message: `确定要取消收藏选中的 ${selectedCount} 个 SKU 吗？`,
      },
    };

    const actionConfig = actions[action as keyof typeof actions];
    if (actionConfig) {
      setConfirmDialog({
        open: true,
        action,
        title: actionConfig.title,
        message: actionConfig.message,
      });
    }
    handleMenuClose();
  };

  const handleConfirmAction = () => {
    onBulkAction(confirmDialog.action);
    setConfirmDialog({ open: false, action: '', title: '', message: '' });
  };

  const handleCancelAction = () => {
    setConfirmDialog({ open: false, action: '', title: '', message: '' });
  };

  return (
    <>
      <Box
        sx={{
          p: 2,
          mb: 2,
          backgroundColor: 'primary.light',
          borderRadius: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Chip
            label={`已选择 ${selectedCount} 个 SKU`}
            color='primary'
            variant='filled'
          />
          <Typography variant='body2' color='primary.contrastText'>
            选择操作来批量处理这些 SKU
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant='contained'
            size='small'
            startIcon={<EditIcon />}
            onClick={() => handleBulkAction('edit')}
          >
            批量编辑
          </Button>
          <Button
            variant='outlined'
            size='small'
            startIcon={<CopyIcon />}
            onClick={() => handleBulkAction('copy')}
          >
            批量复制
          </Button>
          <Button
            variant='outlined'
            size='small'
            startIcon={<StarIcon />}
            onClick={() => handleBulkAction('favorite')}
          >
            批量收藏
          </Button>
          <Button
            variant='outlined'
            size='small'
            startIcon={<MoreVertIcon />}
            onClick={handleMenuOpen}
          >
            更多操作
          </Button>
          <Button
            variant='text'
            size='small'
            onClick={onClearSelection}
            color='inherit'
          >
            取消选择
          </Button>
        </Box>
      </Box>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => handleBulkAction('export')}>
          <ListItemIcon>
            <DownloadIcon />
          </ListItemIcon>
          <ListItemText>导出数据</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleBulkAction('import')}>
          <ListItemIcon>
            <UploadIcon />
          </ListItemIcon>
          <ListItemText>导入数据</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleBulkAction('unfavorite')}>
          <ListItemIcon>
            <StarBorderIcon />
          </ListItemIcon>
          <ListItemText>取消收藏</ListItemText>
        </MenuItem>
        <MenuItem
          onClick={() => handleBulkAction('delete')}
          sx={{ color: 'error.main' }}
        >
          <ListItemIcon>
            <DeleteIcon color='error' />
          </ListItemIcon>
          <ListItemText>批量删除</ListItemText>
        </MenuItem>
      </Menu>

      <Dialog
        open={confirmDialog.open}
        onClose={handleCancelAction}
        maxWidth='sm'
        fullWidth
      >
        <DialogTitle>{confirmDialog.title}</DialogTitle>
        <DialogContent>
          <Typography variant='body1' sx={{ mb: 2 }}>
            {confirmDialog.message}
          </Typography>
          {confirmDialog.action === 'delete' && (
            <Alert severity='warning' sx={{ mt: 2 }}>
              删除操作不可撤销，请谨慎操作！
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelAction}>取消</Button>
          <Button
            onClick={handleConfirmAction}
            variant='contained'
            color={confirmDialog.action === 'delete' ? 'error' : 'primary'}
          >
            确定
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
