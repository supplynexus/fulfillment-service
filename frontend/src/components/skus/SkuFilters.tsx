'use client';

import React, { useState } from 'react';
import {
  Box,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Button,
  Grid,
  Autocomplete,
  Typography,
  Collapse,
  IconButton,
} from '@mui/material';
import {
  FilterList as FilterIcon,
  Clear as ClearIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';

interface FilterOptions {
  search: string;
  status: string;
  category: string;
  dimensions: Record<string, string[]>;
  priceRange: { min: number; max: number };
  inventoryRange: { min: number; max: number };
  isFavorite: boolean | null;
}

interface SkuFiltersProps {
  onFiltersChange: (filters: FilterOptions) => void;
}

export function SkuFilters({ onFiltersChange }: SkuFiltersProps) {
  const [filters, setFilters] = useState<FilterOptions>({
    search: '',
    status: '',
    category: '',
    dimensions: {},
    priceRange: { min: 0, max: 1000 },
    inventoryRange: { min: 0, max: 1000 },
    isFavorite: null,
  });

  const [expanded, setExpanded] = useState(false);

  const handleFilterChange = (key: keyof FilterOptions, value: any) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    onFiltersChange(newFilters);
  };

  const handleDimensionChange = (dimension: string, values: string[]) => {
    const newDimensions = { ...filters.dimensions, [dimension]: values };
    handleFilterChange('dimensions', newDimensions);
  };

  const handleClearFilters = () => {
    const clearedFilters: FilterOptions = {
      search: '',
      status: '',
      category: '',
      dimensions: {},
      priceRange: { min: 0, max: 1000 },
      inventoryRange: { min: 0, max: 1000 },
      isFavorite: null,
    };
    setFilters(clearedFilters);
    onFiltersChange(clearedFilters);
  };

  const getActiveFiltersCount = () => {
    let count = 0;
    if (filters.search) count++;
    if (filters.status) count++;
    if (filters.category) count++;
    if (Object.keys(filters.dimensions).length > 0) count++;
    if (filters.priceRange.min > 0 || filters.priceRange.max < 1000) count++;
    if (filters.inventoryRange.min > 0 || filters.inventoryRange.max < 1000)
      count++;
    if (filters.isFavorite !== null) count++;
    return count;
  };

  const activeFiltersCount = getActiveFiltersCount();

  return (
    <Box>
      {/* 基础筛选器 */}
      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }} alignItems='center'>
        <Box sx={{ width: { xs: "100%", md: "25%" } }}>
          <TextField
            fullWidth
            label='搜索 SKU 或产品名称'
            value={filters.search}
            onChange={e => handleFilterChange('search', e.target.value)}
            size='small'
          />
        </Box>
        <Box sx={{ width: { xs: "100%", md: "16.67%" } }}>
          <FormControl fullWidth size='small'>
            <InputLabel>状态</InputLabel>
            <Select
              value={filters.status}
              onChange={e => handleFilterChange('status', e.target.value)}
              label='状态'
            >
              <MenuItem value=''>全部</MenuItem>
              <MenuItem value='active'>激活</MenuItem>
              <MenuItem value='inactive'>停用</MenuItem>
              <MenuItem value='draft'>草稿</MenuItem>
            </Select>
          </FormControl>
        </Box>
        <Box sx={{ width: { xs: "100%", md: "16.67%" } }}>
          <FormControl fullWidth size='small'>
            <InputLabel>分类</InputLabel>
            <Select
              value={filters.category}
              onChange={e => handleFilterChange('category', e.target.value)}
              label='分类'
            >
              <MenuItem value=''>全部</MenuItem>
              <MenuItem value='clothing'>服装</MenuItem>
              <MenuItem value='electronics'>电子产品</MenuItem>
              <MenuItem value='accessories'>配饰</MenuItem>
            </Select>
          </FormControl>
        </Box>
        <Box sx={{ width: { xs: "100%", md: "16.67%" } }}>
          <FormControl fullWidth size='small'>
            <InputLabel>收藏</InputLabel>
            <Select
              value={
                filters.isFavorite === null ? '' : filters.isFavorite.toString()
              }
              onChange={e => {
                const value =
                  e.target.value === '' ? null : e.target.value === 'true';
                handleFilterChange('isFavorite', value);
              }}
              label='收藏'
            >
              <MenuItem value=''>全部</MenuItem>
              <MenuItem value='true'>已收藏</MenuItem>
              <MenuItem value='false'>未收藏</MenuItem>
            </Select>
          </FormControl>
        </Box>
        <Box sx={{ width: { xs: "100%", md: "25%" } }}>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant='outlined'
              startIcon={<FilterIcon />}
              onClick={() => setExpanded(!expanded)}
              endIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            >
              高级筛选
              {activeFiltersCount > 0 && (
                <Chip
                  label={activeFiltersCount}
                  size='small'
                  color='primary'
                  sx={{ ml: 1, height: 20 }}
                />
              )}
            </Button>
            {activeFiltersCount > 0 && (
              <Button
                variant='outlined'
                startIcon={<ClearIcon />}
                onClick={handleClearFilters}
                color='secondary'
              >
                清除
              </Button>
            )}
          </Box>
        </Box>
      </Box>

      {/* 高级筛选器 */}
      <Collapse in={expanded}>
        <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: 'divider' }}>
          <Typography variant='subtitle2' sx={{ mb: 2 }}>
            高级筛选选项
          </Typography>
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
            {/* 维度筛选 */}
            <Box sx={{ width: { xs: "100%", md: "50%" } }}>
              <Typography variant='body2' sx={{ mb: 1 }}>
                颜色
              </Typography>
              <Autocomplete
                multiple
                size='small'
                options={['黑色', '白色', '红色', '蓝色', '绿色']}
                value={filters.dimensions.color || []}
                onChange={(_, value) => handleDimensionChange('color', value)}
                renderTags={(value, getTagProps) =>
                  value.map((option, index) => (
                    <Chip
                      variant='outlined'
                      label={option}
                      size='small'
                      {...getTagProps({ index })}
                    />
                  ))
                }
                renderInput={params => (
                  <TextField {...params} placeholder='选择颜色' size='small' />
                )}
              />
            </Box>
            <Box sx={{ width: { xs: "100%", md: "50%" } }}>
              <Typography variant='body2' sx={{ mb: 1 }}>
                尺码
              </Typography>
              <Autocomplete
                multiple
                size='small'
                options={['XS', 'S', 'M', 'L', 'XL', 'XXL', '均码']}
                value={filters.dimensions.size || []}
                onChange={(_, value) => handleDimensionChange('size', value)}
                renderTags={(value, getTagProps) =>
                  value.map((option, index) => (
                    <Chip
                      variant='outlined'
                      label={option}
                      size='small'
                      {...getTagProps({ index })}
                    />
                  ))
                }
                renderInput={params => (
                  <TextField {...params} placeholder='选择尺码' size='small' />
                )}
              />
            </Box>

            {/* 价格范围 */}
            <Box sx={{ width: { xs: "100%", md: "50%" } }}>
              <Typography variant='body2' sx={{ mb: 1 }}>
                价格范围
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <TextField
                  type='number'
                  size='small'
                  label='最低价格'
                  value={filters.priceRange.min}
                  onChange={e =>
                    handleFilterChange('priceRange', {
                      ...filters.priceRange,
                      min: Number(e.target.value),
                    })
                  }
                  sx={{ flex: 1 }}
                />
                <Typography variant='body2'>-</Typography>
                <TextField
                  type='number'
                  size='small'
                  label='最高价格'
                  value={filters.priceRange.max}
                  onChange={e =>
                    handleFilterChange('priceRange', {
                      ...filters.priceRange,
                      max: Number(e.target.value),
                    })
                  }
                  sx={{ flex: 1 }}
                />
              </Box>
            </Box>

            {/* 库存范围 */}
            <Box sx={{ width: { xs: "100%", md: "50%" } }}>
              <Typography variant='body2' sx={{ mb: 1 }}>
                库存范围
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <TextField
                  type='number'
                  size='small'
                  label='最低库存'
                  value={filters.inventoryRange.min}
                  onChange={e =>
                    handleFilterChange('inventoryRange', {
                      ...filters.inventoryRange,
                      min: Number(e.target.value),
                    })
                  }
                  sx={{ flex: 1 }}
                />
                <Typography variant='body2'>-</Typography>
                <TextField
                  type='number'
                  size='small'
                  label='最高库存'
                  value={filters.inventoryRange.max}
                  onChange={e =>
                    handleFilterChange('inventoryRange', {
                      ...filters.inventoryRange,
                      max: Number(e.target.value),
                    })
                  }
                  sx={{ flex: 1 }}
                />
              </Box>
            </Box>
          </Box>
        </Box>
      </Collapse>
    </Box>
  );
}
