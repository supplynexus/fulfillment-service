'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Box,
  Typography,
  CircularProgress,
} from '@mui/material';
import { FixedSizeList as List } from 'react-window';

export interface VirtualizedTableProps {
  columns: Array<{
    id: string;
    label: string;
    field: string;
    width?: number;
    align?: 'left' | 'center' | 'right';
    render?: (value: any, row: any) => React.ReactNode;
  }>;
  data: any[];
  height?: number;
  itemHeight?: number;
  loading?: boolean;
  onRowClick?: (row: any, index: number) => void;
  onRowSelect?: (row: any, selected: boolean) => void;
  selectedRows?: Set<string>;
  selectable?: boolean;
}

export function VirtualizedTable({
  columns,
  data,
  height = 400,
  itemHeight = 53,
  loading = false,
  onRowClick,
  onRowSelect,
  selectedRows = new Set(),
  selectable = false,
}: VirtualizedTableProps) {
  const [containerHeight, setContainerHeight] = useState(height);

  // 计算列宽
  const columnWidths = useMemo(() => {
    const totalWidth = columns.reduce((sum, col) => sum + (col.width || 150), 0);
    return columns.map(col => ({
      ...col,
      width: col.width || Math.max(150, (col.width || 150) * (800 / totalWidth))
    }));
  }, [columns]);

  // 行渲染器
  const Row = useCallback(({ index, style }: { index: number; style: React.CSSProperties }) => {
    const row = data[index];
    if (!row) return null;

    const isSelected = selectedRows.has(row.id);

    const handleRowClick = () => {
      onRowClick?.(row, index);
    };

    const handleSelect = (e: React.MouseEvent) => {
      e.stopPropagation();
      onRowSelect?.(row, !isSelected);
    };

    return (
      <div style={style}>
        <TableRow
          hover
          onClick={handleRowClick}
          selected={isSelected}
          sx={{
            cursor: 'pointer',
            '&:hover': {
              backgroundColor: 'action.hover',
            },
            backgroundColor: isSelected ? 'action.selected' : 'inherit',
          }}
        >
          {selectable && (
            <TableCell padding="checkbox">
              <input
                type="checkbox"
                checked={isSelected}
                onChange={handleSelect}
                onClick={handleSelect}
              />
            </TableCell>
          )}
          
          {columnWidths.map((column) => (
            <TableCell
              key={column.id}
              align={column.align || 'left'}
              style={{ width: column.width }}
            >
              {column.render ? column.render(row[column.field], row) : row[column.field]}
            </TableCell>
          ))}
        </TableRow>
      </div>
    );
  }, [data, columnWidths, selectedRows, onRowClick, onRowSelect, selectable]);

  // 表头
  const TableHeader = useMemo(() => (
    <TableHead>
      <TableRow>
        {selectable && (
          <TableCell padding="checkbox">
            <input
              type="checkbox"
              checked={data.length > 0 && selectedRows.size === data.length}
              onChange={(e) => {
                data.forEach(row => onRowSelect?.(row, e.target.checked));
              }}
            />
          </TableCell>
        )}
        
        {columnWidths.map((column) => (
          <TableCell
            key={column.id}
            align={column.align || 'left'}
            style={{ width: column.width }}
          >
            <Typography variant="subtitle2" fontWeight={600}>
              {column.label}
            </Typography>
          </TableCell>
        ))}
      </TableRow>
    </TableHead>
  ), [columnWidths, data.length, selectedRows.size, onRowSelect, selectable]);

  // 加载状态
  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height,
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  // 空数据状态
  if (data.length === 0) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height,
        }}
      >
        <Typography variant="body2" color="text.secondary">
          暂无数据
        </Typography>
      </Box>
    );
  }

  return (
    <TableContainer component={Paper} sx={{ height }}>
      <Table stickyHeader>
        {TableHeader}
      </Table>
      
      <Box sx={{ height: height - 57, overflow: 'hidden' }}>
        <List
          height={height - 57}
          itemCount={data.length}
          itemSize={itemHeight}
          itemData={data}
        >
          {Row}
        </List>
      </Box>
    </TableContainer>
  );
}

// 懒加载Hook
export function useLazyLoading<T>(
  loadFunction: (page: number, pageSize: number) => Promise<T[]>,
  pageSize: number = 50
) {
  const [data, setData] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);

  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;

    setLoading(true);
    try {
      const newData = await loadFunction(page, pageSize);
      setData(prev => [...prev, ...newData]);
      setPage(prev => prev + 1);
      setHasMore(newData.length === pageSize);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  }, [loadFunction, page, pageSize, loading, hasMore]);

  const reset = useCallback(() => {
    setData([]);
    setPage(1);
    setHasMore(true);
    setLoading(false);
  }, []);

  useEffect(() => {
    loadMore();
  }, []);

  return {
    data,
    loading,
    hasMore,
    loadMore,
    reset,
  };
}

// 缓存Hook
export function useDataCache<T>(
  key: string,
  fetchFunction: () => Promise<T>,
  ttl: number = 5 * 60 * 1000 // 5分钟
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const getCachedData = useCallback(() => {
    try {
      const cached = localStorage.getItem(`cache_${key}`);
      if (cached) {
        const { data: cachedData, timestamp } = JSON.parse(cached);
        if (Date.now() - timestamp < ttl) {
          return cachedData;
        }
      }
    } catch (error) {
      console.warn('Failed to get cached data:', error);
    }
    return null;
  }, [key, ttl]);

  const setCachedData = useCallback((data: T) => {
    try {
      localStorage.setItem(`cache_${key}`, JSON.stringify({
        data,
        timestamp: Date.now(),
      }));
    } catch (error) {
      console.warn('Failed to cache data:', error);
    }
  }, [key]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // 先尝试从缓存获取
      const cachedData = getCachedData();
      if (cachedData) {
        setData(cachedData);
        setLoading(false);
        return;
      }

      // 从服务器获取
      const newData = await fetchFunction();
      setData(newData);
      setCachedData(newData);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [fetchFunction, getCachedData, setCachedData]);

  const invalidateCache = useCallback(() => {
    try {
      localStorage.removeItem(`cache_${key}`);
    } catch (error) {
      console.warn('Failed to invalidate cache:', error);
    }
  }, [key]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    refetch: fetchData,
    invalidateCache,
  };
}
