'use client';

import React, { useState, useEffect } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Checkbox,
  IconButton,
  Chip,
  Box,
  Typography,
  Tooltip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Paper,
  Alert,
} from '@mui/material';
import {
  MoreVert as MoreVertIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  ContentCopy as CopyIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
} from '@mui/icons-material';

interface SkuData {
  id: string;
  sku: string;
  productName: string;
  dimensions: Record<string, string>;
  attributes: Record<string, string>;
  price: number;
  cost: number;
  inventory: number;
  status: 'active' | 'inactive' | 'draft';
  isFavorite: boolean;
  createdAt: string;
  updatedAt: string;
}

interface SkuListProps {
  selectedSkus: string[];
  onSelectionChange: (selectedSkus: string[]) => void;
  onSkuAction: (action: string, skuId: string) => void;
}

export function SkuList({
  selectedSkus,
  onSelectionChange,
  onSkuAction,
}: SkuListProps) {
  const [skus, setSkus] = useState<SkuData[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [totalCount, setTotalCount] = useState(0);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedSku, setSelectedSku] = useState<string | null>(null);

  // 模拟数据
  useEffect(() => {
    const mockSkus: SkuData[] = [
      {
        id: '1',
        sku: 'IMP-BLK-S',
        productName: 'IMPEACH BASIC BLACK',
        dimensions: { color: '黑色', size: 'S' },
        attributes: { material: '棉质', brand: 'IMPEACH' },
        price: 29.99,
        cost: 15.0,
        inventory: 100,
        status: 'active',
        isFavorite: false,
        createdAt: '2024-01-15T10:00:00Z',
        updatedAt: '2024-01-15T10:00:00Z',
      },
      {
        id: '2',
        sku: 'IMP-BLK-M',
        productName: 'IMPEACH BASIC BLACK',
        dimensions: { color: '黑色', size: 'M' },
        attributes: { material: '棉质', brand: 'IMPEACH' },
        price: 29.99,
        cost: 15.0,
        inventory: 150,
        status: 'active',
        isFavorite: true,
        createdAt: '2024-01-15T10:00:00Z',
        updatedAt: '2024-01-15T10:00:00Z',
      },
      {
        id: '3',
        sku: 'IMP-BLK-L',
        productName: 'IMPEACH BASIC BLACK',
        dimensions: { color: '黑色', size: 'L' },
        attributes: { material: '棉质', brand: 'IMPEACH' },
        price: 29.99,
        cost: 15.0,
        inventory: 80,
        status: 'active',
        isFavorite: false,
        createdAt: '2024-01-15T10:00:00Z',
        updatedAt: '2024-01-15T10:00:00Z',
      },
    ];

    setTimeout(() => {
      setSkus(mockSkus);
      setTotalCount(mockSkus.length);
      setLoading(false);
    }, 1000);
  }, []);

  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      const newSelected = skus.map(sku => sku.id);
      onSelectionChange(newSelected);
    } else {
      onSelectionChange([]);
    }
  };

  const handleSelectSku = (skuId: string) => {
    const newSelected = selectedSkus.includes(skuId)
      ? selectedSkus.filter(id => id !== skuId)
      : [...selectedSkus, skuId];
    onSelectionChange(newSelected);
  };

  const handleMenuOpen = (
    event: React.MouseEvent<HTMLElement>,
    skuId: string
  ) => {
    setAnchorEl(event.currentTarget);
    setSelectedSku(skuId);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedSku(null);
  };

  const handleSkuAction = (action: string) => {
    if (selectedSku) {
      onSkuAction(action, selectedSku);
    }
    handleMenuClose();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'inactive':
        return 'error';
      case 'draft':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'active':
        return '激活';
      case 'inactive':
        return '停用';
      case 'draft':
        return '草稿';
      default:
        return status;
    }
  };

  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: 400,
        }}
      >
        <Typography>加载中...</Typography>
      </Box>
    );
  }

  if (skus.length === 0) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Alert severity='info'>
          暂无 SKU 数据。请先创建产品或从外部系统同步商品。
        </Alert>
      </Box>
    );
  }

  return (
    <>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell padding='checkbox'>
                <Checkbox
                  indeterminate={
                    selectedSkus.length > 0 && selectedSkus.length < skus.length
                  }
                  checked={
                    skus.length > 0 && selectedSkus.length === skus.length
                  }
                  onChange={handleSelectAll}
                />
              </TableCell>
              <TableCell>SKU</TableCell>
              <TableCell>产品名称</TableCell>
              <TableCell>维度</TableCell>
              <TableCell>属性</TableCell>
              <TableCell>价格</TableCell>
              <TableCell>成本</TableCell>
              <TableCell>库存</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>收藏</TableCell>
              <TableCell align='right'>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {skus.map(sku => (
              <TableRow key={sku.id} hover>
                <TableCell padding='checkbox'>
                  <Checkbox
                    checked={selectedSkus.includes(sku.id)}
                    onChange={() => handleSelectSku(sku.id)}
                  />
                </TableCell>
                <TableCell>
                  <Typography variant='body2' sx={{ fontFamily: 'monospace' }}>
                    {sku.sku}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant='body2' noWrap>
                    {sku.productName}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {Object.entries(sku.dimensions).map(([key, value]) => (
                      <Chip
                        key={key}
                        label={`${key}: ${value}`}
                        size='small'
                        variant='outlined'
                      />
                    ))}
                  </Box>
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {Object.entries(sku.attributes).map(([key, value]) => (
                      <Chip
                        key={key}
                        label={`${key}: ${value}`}
                        size='small'
                        variant='outlined'
                        color='secondary'
                      />
                    ))}
                  </Box>
                </TableCell>
                <TableCell>
                  <Typography variant='body2' sx={{ fontWeight: 600 }}>
                    ¥{sku.price.toFixed(2)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant='body2' color='text.secondary'>
                    ¥{sku.cost.toFixed(2)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography
                    variant='body2'
                    color={sku.inventory < 10 ? 'error' : 'text.primary'}
                    sx={{ fontWeight: sku.inventory < 10 ? 600 : 400 }}
                  >
                    {sku.inventory}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    label={getStatusLabel(sku.status)}
                    color={getStatusColor(sku.status) as any}
                    size='small'
                  />
                </TableCell>
                <TableCell>
                  <IconButton
                    size='small'
                    onClick={() => console.log('Toggle favorite:', sku.id)}
                  >
                    {sku.isFavorite ? (
                      <StarIcon color='warning' />
                    ) : (
                      <StarBorderIcon />
                    )}
                  </IconButton>
                </TableCell>
                <TableCell align='right'>
                  <Tooltip title='更多操作'>
                    <IconButton
                      size='small'
                      onClick={e => handleMenuOpen(e, sku.id)}
                    >
                      <MoreVertIcon />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <TablePagination
        rowsPerPageOptions={[10, 25, 50, 100]}
        component='div'
        count={totalCount}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={(event, newPage) => setPage(newPage)}
        onRowsPerPageChange={event => {
          setRowsPerPage(parseInt(event.target.value, 10));
          setPage(0);
        }}
        labelRowsPerPage='每页行数:'
        labelDisplayedRows={({ from, to, count }) =>
          `${from}-${to} 共 ${count} 条`
        }
      />

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => handleSkuAction('view')}>
          <ListItemIcon>
            <ViewIcon />
          </ListItemIcon>
          <ListItemText>查看详情</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleSkuAction('edit')}>
          <ListItemIcon>
            <EditIcon />
          </ListItemIcon>
          <ListItemText>编辑</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleSkuAction('copy')}>
          <ListItemIcon>
            <CopyIcon />
          </ListItemIcon>
          <ListItemText>复制</ListItemText>
        </MenuItem>
        <MenuItem
          onClick={() => handleSkuAction('delete')}
          sx={{ color: 'error.main' }}
        >
          <ListItemIcon>
            <DeleteIcon color='error' />
          </ListItemIcon>
          <ListItemText>删除</ListItemText>
        </MenuItem>
      </Menu>
    </>
  );
}
