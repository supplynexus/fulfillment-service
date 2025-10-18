'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Checkbox,
  IconButton,
  Tooltip,
  Box,
  Typography,
  Chip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  FormControlLabel,
  Switch,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Sort as SortIcon,
  FilterList as FilterIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';

export interface Column {
  id: string;
  label: string;
  field: string;
  type: 'text' | 'number' | 'date' | 'boolean' | 'chip' | 'action';
  sortable?: boolean;
  filterable?: boolean;
  width?: number;
  align?: 'left' | 'center' | 'right';
  render?: (value: any, row: any) => React.ReactNode;
  hidden?: boolean;
}

export interface DynamicTableProps {
  columns: Column[];
  data: any[];
  loading?: boolean;
  onSort?: (field: string, direction: 'asc' | 'desc') => void;
  onFilter?: (filters: Record<string, any>) => void;
  onRowSelect?: (selectedRows: any[]) => void;
  onColumnConfig?: (columns: Column[]) => void;
  selectable?: boolean;
  sortable?: boolean;
  filterable?: boolean;
  exportable?: boolean;
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
    onPageSizeChange: (pageSize: number) => void;
  };
}

export function DynamicTable({
  columns,
  data,
  loading = false,
  onSort,
  onFilter,
  onRowSelect,
  onColumnConfig,
  selectable = false,
  sortable = true,
  filterable = true,
  exportable = true,
  pagination,
}: DynamicTableProps) {
  const [visibleColumns, setVisibleColumns] = useState<Column[]>([]);
  const [selectedRows, setSelectedRows] = useState<any[]>([]);
  const [sortField, setSortField] = useState<string>('');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [columnMenuAnchor, setColumnMenuAnchor] = useState<null | HTMLElement>(null);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [columnConfig, setColumnConfig] = useState<Column[]>([]);

  useEffect(() => {
    const initialColumns = columns.filter(col => !col.hidden);
    setVisibleColumns(initialColumns);
    setColumnConfig(columns);
  }, [columns]);

  const handleSort = (field: string) => {
    if (!sortable) return;
    
    const newDirection = sortField === field && sortDirection === 'asc' ? 'desc' : 'asc';
    setSortField(field);
    setSortDirection(newDirection);
    onSort?.(field, newDirection);
  };

  const handleRowSelect = (row: any, checked: boolean) => {
    if (!selectable) return;
    
    let newSelectedRows;
    if (checked) {
      newSelectedRows = [...selectedRows, row];
    } else {
      newSelectedRows = selectedRows.filter(r => r.id !== row.id);
    }
    setSelectedRows(newSelectedRows);
    onRowSelect?.(newSelectedRows);
  };

  const handleSelectAll = (checked: boolean) => {
    if (!selectable) return;
    
    const newSelectedRows = checked ? [...data] : [];
    setSelectedRows(newSelectedRows);
    onRowSelect?.(newSelectedRows);
  };

  const handleColumnToggle = (columnId: string, visible: boolean) => {
    const updatedColumns = columnConfig.map(col => 
      col.id === columnId ? { ...col, hidden: !visible } : col
    );
    setColumnConfig(updatedColumns);
    
    const newVisibleColumns = updatedColumns.filter(col => !col.hidden);
    setVisibleColumns(newVisibleColumns);
    onColumnConfig?.(updatedColumns);
  };

  const handleColumnReorder = (fromIndex: number, toIndex: number) => {
    const newColumns = [...columnConfig];
    const [movedColumn] = newColumns.splice(fromIndex, 1);
    newColumns.splice(toIndex, 0, movedColumn);
    setColumnConfig(newColumns);
    
    const newVisibleColumns = newColumns.filter(col => !col.hidden);
    setVisibleColumns(newVisibleColumns);
    onColumnConfig?.(newColumns);
  };

  const renderCell = (column: Column, row: any) => {
    const value = row[column.field];
    
    if (column.render) {
      return column.render(value, row);
    }

    switch (column.type) {
      case 'boolean':
        return (
          <Chip
            label={value ? '是' : '否'}
            color={value ? 'success' : 'default'}
            size="small"
          />
        );
      case 'chip':
        return (
          <Chip
            label={value}
            size="small"
            color="primary"
          />
        );
      case 'date':
        return value ? new Date(value).toLocaleDateString() : '-';
      case 'number':
        return typeof value === 'number' ? value.toLocaleString() : value;
      default:
        return value || '-';
    }
  };

  const getSortIcon = (field: string) => {
    if (sortField !== field) return <SortIcon />;
    return sortDirection === 'asc' ? <SortIcon /> : <SortIcon style={{ transform: 'rotate(180deg)' }} />;
  };

  const exportData = () => {
    const csvContent = [
      visibleColumns.map(col => col.label).join(','),
      ...data.map(row => 
        visibleColumns.map(col => {
          const value = row[col.field];
          return typeof value === 'string' && value.includes(',') ? `"${value}"` : value;
        }).join(',')
      )
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'export.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Box>
      {/* 工具栏 */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {selectable && (
            <Typography variant="body2" color="text.secondary">
              已选择 {selectedRows.length} 项
            </Typography>
          )}
        </Box>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="列配置">
            <IconButton
              onClick={(e) => setColumnMenuAnchor(e.currentTarget)}
              size="small"
            >
              <SettingsIcon />
            </IconButton>
          </Tooltip>
          
          {exportable && (
            <Tooltip title="导出数据">
              <IconButton onClick={exportData} size="small">
                <DownloadIcon />
              </IconButton>
            </Tooltip>
          )}
          
          <Tooltip title="刷新">
            <IconButton onClick={() => window.location.reload()} size="small">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* 表格 */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              {selectable && (
                <TableCell padding="checkbox">
                  <Checkbox
                    indeterminate={selectedRows.length > 0 && selectedRows.length < data.length}
                    checked={data.length > 0 && selectedRows.length === data.length}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                  />
                </TableCell>
              )}
              
              {visibleColumns.map((column) => (
                <TableCell
                  key={column.id}
                  align={column.align || 'left'}
                  style={{ width: column.width }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="subtitle2">
                      {column.label}
                    </Typography>
                    
                    {column.sortable && sortable && (
                      <IconButton
                        size="small"
                        onClick={() => handleSort(column.field)}
                      >
                        {getSortIcon(column.field)}
                      </IconButton>
                    )}
                  </Box>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          
          <TableBody>
            {data.map((row, index) => (
              <TableRow key={row.id || index} hover>
                {selectable && (
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={selectedRows.some(r => r.id === row.id)}
                      onChange={(e) => handleRowSelect(row, e.target.checked)}
                    />
                  </TableCell>
                )}
                
                {visibleColumns.map((column) => (
                  <TableCell
                    key={column.id}
                    align={column.align || 'left'}
                  >
                    {renderCell(column, row)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* 列配置菜单 */}
      <Menu
        anchorEl={columnMenuAnchor}
        open={Boolean(columnMenuAnchor)}
        onClose={() => setColumnMenuAnchor(null)}
      >
        <MenuItem onClick={() => setConfigDialogOpen(true)}>
          <ListItemIcon>
            <SettingsIcon />
          </ListItemIcon>
          <ListItemText>列配置</ListItemText>
        </MenuItem>
      </Menu>

      {/* 列配置对话框 */}
      <Dialog
        open={configDialogOpen}
        onClose={() => setConfigDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>列配置</DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            {columnConfig.map((column, index) => (
              <Box key={column.id} sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={!column.hidden}
                      onChange={(e) => handleColumnToggle(column.id, e.target.checked)}
                    />
                  }
                  label={column.label}
                />
              </Box>
            ))}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfigDialogOpen(false)}>
            取消
          </Button>
          <Button onClick={() => setConfigDialogOpen(false)} variant="contained">
            确定
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
