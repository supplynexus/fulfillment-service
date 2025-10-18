'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Grid,
  Typography,
  Paper,
  Collapse,
  IconButton,
  Chip,
  Autocomplete,
  Slider,
  FormControlLabel,
  Switch,
  Divider,
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  Clear as ClearIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Save as SaveIcon,
  Bookmark as BookmarkIcon,
} from '@mui/icons-material';

export interface SearchFilter {
  id: string;
  field: string;
  operator: string;
  value: any;
  label: string;
  type: 'text' | 'select' | 'number' | 'date' | 'boolean' | 'multiselect' | 'range';
  options?: any[];
  min?: number;
  max?: number;
}

export interface AdvancedSearchProps {
  fields: Array<{
    key: string;
    label: string;
    type: 'text' | 'select' | 'number' | 'date' | 'boolean' | 'multiselect' | 'range';
    options?: any[];
    min?: number;
    max?: number;
  }>;
  onSearch: (filters: SearchFilter[]) => void;
  onClear: () => void;
  onSaveSearch?: (name: string, filters: SearchFilter[]) => void;
  onLoadSearch?: (name: string) => SearchFilter[];
  savedSearches?: string[];
  loading?: boolean;
}

export function AdvancedSearch({
  fields,
  onSearch,
  onClear,
  onSaveSearch,
  onLoadSearch,
  savedSearches = [],
  loading = false,
}: AdvancedSearchProps) {
  const [filters, setFilters] = useState<SearchFilter[]>([]);
  const [expanded, setExpanded] = useState(false);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [searchName, setSearchName] = useState('');

  const operators = {
    text: [
      { value: 'contains', label: '包含' },
      { value: 'equals', label: '等于' },
      { value: 'starts_with', label: '开头是' },
      { value: 'ends_with', label: '结尾是' },
      { value: 'regex', label: '正则表达式' },
    ],
    select: [
      { value: 'equals', label: '等于' },
      { value: 'not_equals', label: '不等于' },
      { value: 'in', label: '在列表中' },
      { value: 'not_in', label: '不在列表中' },
    ],
    number: [
      { value: 'equals', label: '等于' },
      { value: 'not_equals', label: '不等于' },
      { value: 'greater_than', label: '大于' },
      { value: 'less_than', label: '小于' },
      { value: 'between', label: '在范围内' },
    ],
    date: [
      { value: 'equals', label: '等于' },
      { value: 'after', label: '晚于' },
      { value: 'before', label: '早于' },
      { value: 'between', label: '在范围内' },
    ],
    boolean: [
      { value: 'equals', label: '等于' },
    ],
    multiselect: [
      { value: 'in', label: '在列表中' },
      { value: 'not_in', label: '不在列表中' },
    ],
    range: [
      { value: 'between', label: '在范围内' },
    ],
  };

  const addFilter = () => {
    const newFilter: SearchFilter = {
      id: Date.now().toString(),
      field: fields[0]?.key || '',
      operator: 'equals',
      value: '',
      label: fields[0]?.label || '',
      type: fields[0]?.type || 'text',
    };
    setFilters([...filters, newFilter]);
  };

  const removeFilter = (id: string) => {
    setFilters(filters.filter(f => f.id !== id));
  };

  const updateFilter = (id: string, updates: Partial<SearchFilter>) => {
    setFilters(filters.map(f => 
      f.id === id ? { ...f, ...updates } : f
    ));
  };

  const handleSearch = () => {
    onSearch(filters);
  };

  const handleClear = () => {
    setFilters([]);
    onClear();
  };

  const handleSaveSearch = () => {
    if (searchName && onSaveSearch) {
      onSaveSearch(searchName, filters);
      setSaveDialogOpen(false);
      setSearchName('');
    }
  };

  const handleLoadSearch = (name: string) => {
    if (onLoadSearch) {
      const loadedFilters = onLoadSearch(name);
      setFilters(loadedFilters);
    }
  };

  const renderFilterValue = (filter: SearchFilter) => {
    const field = fields.find(f => f.key === filter.field);
    if (!field) return null;

    switch (filter.type) {
      case 'text':
        return (
          <TextField
            fullWidth
            size="small"
            value={filter.value}
            onChange={(e) => updateFilter(filter.id, { value: e.target.value })}
            placeholder="输入搜索值"
          />
        );

      case 'select':
        return (
          <FormControl fullWidth size="small">
            <Select
              value={filter.value}
              onChange={(e) => updateFilter(filter.id, { value: e.target.value })}
            >
              {field.options?.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        );

      case 'number':
        return (
          <TextField
            fullWidth
            size="small"
            type="number"
            value={filter.value}
            onChange={(e) => updateFilter(filter.id, { value: e.target.value })}
            placeholder="输入数值"
          />
        );

      case 'date':
        return (
          <TextField
            fullWidth
            size="small"
            type="date"
            value={filter.value}
            onChange={(e) => updateFilter(filter.id, { value: e.target.value })}
            InputLabelProps={{ shrink: true }}
          />
        );

      case 'boolean':
        return (
          <FormControl fullWidth size="small">
            <Select
              value={filter.value}
              onChange={(e) => updateFilter(filter.id, { value: e.target.value })}
            >
              <MenuItem value="true">是</MenuItem>
              <MenuItem value="false">否</MenuItem>
            </Select>
          </FormControl>
        );

      case 'multiselect':
        return (
          <Autocomplete
            multiple
            size="small"
            options={field.options || []}
            value={filter.value || []}
            onChange={(_, value) => updateFilter(filter.id, { value })}
            renderInput={(params) => (
              <TextField {...params} placeholder="选择多个值" />
            )}
            renderTags={(value, getTagProps) =>
              value.map((option, index) => (
                <Chip
                  key={index}
                  label={option.label || option}
                  {...getTagProps({ index })}
                  size="small"
                />
              ))
            }
          />
        );

      case 'range':
        return (
          <Box sx={{ px: 2 }}>
            <Slider
              value={filter.value || [field.min || 0, field.max || 100]}
              onChange={(_, value) => updateFilter(filter.id, { value })}
              valueLabelDisplay="auto"
              min={field.min || 0}
              max={field.max || 100}
              step={1}
            />
          </Box>
        );

      default:
        return null;
    }
  };

  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6" component="h2">
          高级搜索
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <IconButton
            onClick={() => setExpanded(!expanded)}
            size="small"
          >
            {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
          {savedSearches.length > 0 && (
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <Select
                value=""
                onChange={(e) => handleLoadSearch(e.target.value)}
                displayEmpty
              >
                <MenuItem value="" disabled>
                  加载已保存的搜索
                </MenuItem>
                {savedSearches.map((name) => (
                  <MenuItem key={name} value={name}>
                    {name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
        </Box>
      </Box>

      <Collapse in={expanded}>
        <Box sx={{ mb: 2 }}>
          {filters.map((filter) => (
            <Box key={filter.id} sx={{ mb: 2, p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
              <Grid container spacing={2} alignItems="center">
                <Grid item xs={12} sm={3}>
                  <FormControl fullWidth size="small">
                    <InputLabel>字段</InputLabel>
                    <Select
                      value={filter.field}
                      onChange={(e) => {
                        const field = fields.find(f => f.key === e.target.value);
                        updateFilter(filter.id, { 
                          field: e.target.value,
                          label: field?.label || '',
                          type: field?.type || 'text',
                          operator: 'equals',
                          value: ''
                        });
                      }}
                      label="字段"
                    >
                      {fields.map((field) => (
                        <MenuItem key={field.key} value={field.key}>
                          {field.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} sm={2}>
                  <FormControl fullWidth size="small">
                    <InputLabel>操作符</InputLabel>
                    <Select
                      value={filter.operator}
                      onChange={(e) => updateFilter(filter.id, { operator: e.target.value })}
                      label="操作符"
                    >
                      {operators[filter.type]?.map((op) => (
                        <MenuItem key={op.value} value={op.value}>
                          {op.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} sm={5}>
                  {renderFilterValue(filter)}
                </Grid>

                <Grid item xs={12} sm={2}>
                  <IconButton
                    onClick={() => removeFilter(filter.id)}
                    color="error"
                    size="small"
                  >
                    <ClearIcon />
                  </IconButton>
                </Grid>
              </Grid>
            </Box>
          ))}

          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            <Button
              variant="outlined"
              startIcon={<FilterIcon />}
              onClick={addFilter}
              size="small"
            >
              添加筛选条件
            </Button>
            <Button
              variant="outlined"
              startIcon={<ClearIcon />}
              onClick={handleClear}
              size="small"
            >
              清空
            </Button>
            {onSaveSearch && (
              <Button
                variant="outlined"
                startIcon={<SaveIcon />}
                onClick={() => setSaveDialogOpen(true)}
                size="small"
              >
                保存搜索
              </Button>
            )}
          </Box>

          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="contained"
              startIcon={<SearchIcon />}
              onClick={handleSearch}
              disabled={loading || filters.length === 0}
            >
              搜索
            </Button>
            <Button
              variant="outlined"
              onClick={handleClear}
              disabled={loading}
            >
              重置
            </Button>
          </Box>
        </Box>
      </Collapse>

      {/* 保存搜索对话框 */}
      {saveDialogOpen && (
        <Box sx={{ mt: 2, p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            保存搜索条件
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <TextField
              size="small"
              placeholder="输入搜索名称"
              value={searchName}
              onChange={(e) => setSearchName(e.target.value)}
              sx={{ flexGrow: 1 }}
            />
            <Button
              variant="contained"
              onClick={handleSaveSearch}
              disabled={!searchName}
              size="small"
            >
              保存
            </Button>
            <Button
              variant="outlined"
              onClick={() => setSaveDialogOpen(false)}
              size="small"
            >
              取消
            </Button>
          </Box>
        </Box>
      )}
    </Paper>
  );
}
