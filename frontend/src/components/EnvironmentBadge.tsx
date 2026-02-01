'use client';

import { Box, Chip, Typography } from '@mui/material';
import { useMemo } from 'react';

export function EnvironmentBadge() {
  const environment = useMemo(() => {
    return process.env.NEXT_PUBLIC_ENVIRONMENT || 'local';
  }, []);

  const version = useMemo(() => {
    // 优先使用环境变量，如果没有则使用 package.json 中的版本
    return process.env.NEXT_PUBLIC_VERSION || process.env.npm_package_version || '1.0.0';
  }, []);

  const getEnvironmentColor = (env: string) => {
    switch (env.toLowerCase()) {
      case 'prod':
      case 'production':
        return 'error'; // 红色 - 生产环境
      case 'dev':
      case 'development':
        return 'warning'; // 橙色 - 开发环境
      case 'local':
      default:
        return 'info'; // 蓝色 - 本地环境
    }
  };

  const getEnvironmentLabel = (env: string) => {
    switch (env.toLowerCase()) {
      case 'prod':
      case 'production':
        return 'PROD';
      case 'dev':
      case 'development':
        return 'DEV';
      case 'local':
      default:
        return 'LOCAL';
    }
  };

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 8,
        right: 8,
        zIndex: 9999,
        display: 'flex',
        gap: 1,
        alignItems: 'center',
      }}
    >
      <Chip
        label={getEnvironmentLabel(environment)}
        color={getEnvironmentColor(environment)}
        size='small'
        sx={{
          fontWeight: 'bold',
          fontSize: '0.75rem',
        }}
      />
      <Typography
        variant='caption'
        sx={{
          color: 'text.secondary',
          fontSize: '0.7rem',
          fontFamily: 'monospace',
        }}
      >
        v{version}
      </Typography>
    </Box>
  );
}
