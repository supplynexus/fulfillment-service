'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  IconButton,
  Tooltip,
  Chip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  CircularProgress,
  Alert,
  List,
  ListItem,
  Collapse,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ChevronRight as ChevronRightIcon,
  Category as CategoryIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Link as LinkIcon,
  Settings as SettingsIcon,
  MoreVert as MoreVertIcon,
  Add as AddIcon,
} from '@mui/icons-material';

interface CategoryNode {
  id: string;
  name: string;
  label: string;
  code: string;
  description?: string;
  isActive: boolean;
  isRoot: boolean;
  level: number;
  children?: CategoryNode[];
  parents?: CategoryNode[];
  dimensions?: any[];
  productCount?: number;
}

interface CategoryTreeProps {
  onCategorySelect: (category: CategoryNode | null) => void;
  onCategoryEdit: (category: CategoryNode) => void;
  onCategoryDelete: (category: CategoryNode) => void;
  onManageRelations: (category: CategoryNode) => void;
  onManageDimensions: (category: CategoryNode) => void;
}

export function CategoryTree({
  onCategorySelect,
  onCategoryEdit,
  onCategoryDelete,
  onManageRelations,
  onManageDimensions,
}: CategoryTreeProps) {
  const [categories, setCategories] = useState<CategoryNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string[]>([]);
  const [selected, setSelected] = useState<string>('');
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedCategory, setSelectedCategory] = useState<CategoryNode | null>(
    null
  );

  // 模拟数据
  useEffect(() => {
    const mockCategories: CategoryNode[] = [
      {
        id: '1',
        name: '服装',
        label: '服装',
        code: 'clothing',
        description: '所有服装类产品',
        isActive: true,
        isRoot: true,
        level: 0,
        productCount: 150,
        children: [
          {
            id: '2',
            name: '男装',
            label: '男装',
            code: 'mens-clothing',
            description: '男性服装',
            isActive: true,
            isRoot: false,
            level: 1,
            productCount: 80,
            children: [
              {
                id: '3',
                name: 'T恤',
                label: 'T恤',
                code: 'mens-tshirts',
                description: '男性T恤',
                isActive: true,
                isRoot: false,
                level: 2,
                productCount: 40,
                dimensions: [
                  { name: '颜色', code: 'color', required: true },
                  { name: '尺码', code: 'size', required: true },
                ],
              },
              {
                id: '4',
                name: '衬衫',
                label: '衬衫',
                code: 'mens-shirts',
                description: '男性衬衫',
                isActive: true,
                isRoot: false,
                level: 2,
                productCount: 40,
                dimensions: [
                  { name: '颜色', code: 'color', required: true },
                  { name: '尺码', code: 'size', required: true },
                  { name: '材质', code: 'material', required: false },
                ],
              },
            ],
          },
          {
            id: '5',
            name: '女装',
            label: '女装',
            code: 'womens-clothing',
            description: '女性服装',
            isActive: true,
            isRoot: false,
            level: 1,
            productCount: 70,
            children: [
              {
                id: '6',
                name: '连衣裙',
                label: '连衣裙',
                code: 'womens-dresses',
                description: '女性连衣裙',
                isActive: true,
                isRoot: false,
                level: 2,
                productCount: 35,
                dimensions: [
                  { name: '颜色', code: 'color', required: true },
                  { name: '尺码', code: 'size', required: true },
                  { name: '款式', code: 'style', required: false },
                ],
              },
            ],
          },
        ],
      },
      {
        id: '7',
        name: '电子产品',
        label: '电子产品',
        code: 'electronics',
        description: '所有电子产品',
        isActive: true,
        isRoot: true,
        level: 0,
        productCount: 200,
        children: [
          {
            id: '8',
            name: '手机',
            label: '手机',
            code: 'phones',
            description: '手机及配件',
            isActive: true,
            isRoot: false,
            level: 1,
            productCount: 100,
            dimensions: [
              { name: '品牌', code: 'brand', required: true },
              { name: '型号', code: 'model', required: true },
              { name: '颜色', code: 'color', required: true },
            ],
          },
          {
            id: '9',
            name: '电脑',
            label: '电脑',
            code: 'computers',
            description: '电脑及配件',
            isActive: true,
            isRoot: false,
            level: 1,
            productCount: 100,
            dimensions: [
              { name: '品牌', code: 'brand', required: true },
              { name: '型号', code: 'model', required: true },
              { name: '配置', code: 'spec', required: true },
            ],
          },
        ],
      },
    ];

    setTimeout(() => {
      setCategories(mockCategories);
      setExpanded(['1', '2', '5', '7', '8', '9']); // 默认展开一些节点
      setLoading(false);
    }, 1000);
  }, []);

  const handleToggle = (categoryId: string) => {
    setExpanded(prev =>
      prev.includes(categoryId)
        ? prev.filter(id => id !== categoryId)
        : [...prev, categoryId]
    );
  };

  const handleSelect = (category: CategoryNode) => {
    setSelected(category.id);
    onCategorySelect(category);
  };

  const findCategoryById = (
    categories: CategoryNode[],
    id: string
  ): CategoryNode | null => {
    for (const category of categories) {
      if (category.id === id) {
        return category;
      }
      if (category.children) {
        const found = findCategoryById(category.children, id);
        if (found) return found;
      }
    }
    return null;
  };

  const handleMenuOpen = (
    event: React.MouseEvent<HTMLElement>,
    category: CategoryNode
  ) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
    setSelectedCategory(category);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedCategory(null);
  };

  const handleMenuAction = (action: string) => {
    if (!selectedCategory) return;

    switch (action) {
      case 'edit':
        onCategoryEdit(selectedCategory);
        break;
      case 'delete':
        onCategoryDelete(selectedCategory);
        break;
      case 'relations':
        onManageRelations(selectedCategory);
        break;
      case 'dimensions':
        onManageDimensions(selectedCategory);
        break;
    }
    handleMenuClose();
  };

  const renderCategoryItem = (
    category: CategoryNode,
    level: number = 0
  ): React.ReactNode => {
    const hasChildren = category.children && category.children.length > 0;
    const isExpanded = expanded.includes(category.id);
    const isSelected = selected === category.id;

    return (
      <Box key={category.id}>
        <ListItem
          onClick={() => handleSelect(category)}
          selected={isSelected}
          sx={{
            pl: 2 + level * 2,
            backgroundColor: isSelected ? 'action.selected' : 'transparent',
            cursor: 'pointer',
            '&:hover': {
              backgroundColor: 'action.hover',
            },
          }}
        >
          <IconButton
            size='small'
            onClick={e => {
              e.stopPropagation();
              handleToggle(category.id);
            }}
            sx={{ mr: 1 }}
          >
            {hasChildren ? (
              isExpanded ? (
                <ExpandMoreIcon />
              ) : (
                <ChevronRightIcon />
              )
            ) : (
              <Box sx={{ width: 24, height: 24 }} />
            )}
          </IconButton>

          <CategoryIcon sx={{ mr: 1, fontSize: 20 }} />

          <Typography variant='body2' sx={{ flexGrow: 1 }}>
            {category.name}
          </Typography>

          <Box sx={{ display: 'flex', gap: 0.5, mr: 1 }}>
            {category.isRoot && (
              <Chip label='根' size='small' color='primary' />
            )}
            {!category.isActive && (
              <Chip label='停用' size='small' color='error' />
            )}
            {category.productCount && category.productCount > 0 && (
              <Chip
                label={category.productCount}
                size='small'
                variant='outlined'
              />
            )}
          </Box>

          <Tooltip title='更多操作'>
            <IconButton size='small' onClick={e => handleMenuOpen(e, category)}>
              <MoreVertIcon fontSize='small' />
            </IconButton>
          </Tooltip>
        </ListItem>

        {hasChildren && (
          <Collapse in={isExpanded} timeout='auto' unmountOnExit>
            <List component='div' disablePadding>
              {category.children?.map(child =>
                renderCategoryItem(child, level + 1)
              )}
            </List>
          </Collapse>
        )}
      </Box>
    );
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
        <CircularProgress />
      </Box>
    );
  }

  if (categories.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity='info'>暂无分类数据</Alert>
      </Box>
    );
  }

  return (
    <>
      <List sx={{ height: 500, overflowY: 'auto' }}>
        {categories.map(category => renderCategoryItem(category))}
      </List>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => handleMenuAction('edit')}>
          <ListItemIcon>
            <EditIcon />
          </ListItemIcon>
          <ListItemText>编辑分类</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleMenuAction('relations')}>
          <ListItemIcon>
            <LinkIcon />
          </ListItemIcon>
          <ListItemText>管理关系</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleMenuAction('dimensions')}>
          <ListItemIcon>
            <SettingsIcon />
          </ListItemIcon>
          <ListItemText>管理维度</ListItemText>
        </MenuItem>
        <MenuItem
          onClick={() => handleMenuAction('delete')}
          sx={{ color: 'error.main' }}
        >
          <ListItemIcon>
            <DeleteIcon color='error' />
          </ListItemIcon>
          <ListItemText>删除分类</ListItemText>
        </MenuItem>
      </Menu>
    </>
  );
}
