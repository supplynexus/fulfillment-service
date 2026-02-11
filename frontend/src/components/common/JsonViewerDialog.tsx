'use client';

import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  CircularProgress,
} from '@mui/material';
import JsonView from '@uiw/react-json-view';
import { vscodeTheme } from '@uiw/react-json-view/vscode';
import React from 'react';

interface JsonViewerDialogProps {
  open: boolean;
  title: string;
  subtitle?: string;
  data: unknown;
  loading?: boolean;
  onClose: () => void;
}

export function JsonViewerDialog({
  open,
  title,
  subtitle,
  data,
  loading = false,
  onClose,
}: JsonViewerDialogProps) {
  const handleCopy = async () => {
    if (!data) return;
    await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth='lg' fullWidth>
      <DialogTitle>
        <Typography component='div' variant='h6'>
          {title}
        </Typography>
        {subtitle ? (
          <Typography component='div' variant='body2' color='text.secondary'>
            {subtitle}
          </Typography>
        ) : null}
      </DialogTitle>
      <DialogContent>
        {loading ? (
          <Box
            sx={{
              minHeight: 240,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <CircularProgress />
          </Box>
        ) : (
          <Box
            sx={{
              mt: 1,
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 1,
              p: 1,
              maxHeight: '70vh',
              overflow: 'auto',
              backgroundColor: '#111827',
            }}
          >
            <JsonView
              value={(data as object) || {}}
              style={vscodeTheme}
              collapsed={2}
            />
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>关闭</Button>
        <Button
          onClick={handleCopy}
          variant='outlined'
          disabled={loading || !data}
        >
          复制 JSON
        </Button>
      </DialogActions>
    </Dialog>
  );
}
