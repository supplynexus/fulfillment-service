'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Box,
  TextField,
  Button,
  Typography,
  Paper,
  InputAdornment,
  IconButton,
  Alert,
  CircularProgress,
} from '@mui/material';
import { Visibility, VisibilityOff, Person, Lock, Business } from '@mui/icons-material';

import { useAuth } from '@/lib/auth-context';
import { LoginCredentials } from '@/types/auth';

// Validation schema
const loginSchema = z.object({
  username: z
    .string()
    .min(1, '用户名不能为空')
    .min(3, '用户名至少需要3个字符'),
  password: z
    .string()
    .min(1, '密码不能为空')
    .min(6, '密码至少需要6个字符'),
  tenantName: z
    .string()
    .min(1, '租户名称不能为空')
    .min(2, '租户名称至少需要2个字符'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export function LoginForm() {
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login, isLoading } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: '',
      password: '',
      tenantName: '',
    },
  });

  const onSubmit = async (data: LoginFormData) => {
    try {
      setError(null);
      const credentials: LoginCredentials = {
        username: data.username,
        password: data.password,
        tenantName: data.tenantName,
      };
      await login(credentials);
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 
        err.message || 
        '登录失败，请检查您的凭据'
      );
    }
  };

  const handleTogglePasswordVisibility = () => {
    setShowPassword(!showPassword);
  };

  return (
    <Paper
      elevation={3}
      sx={{
        p: 4,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        borderRadius: 2,
      }}
    >
      <Box component="form" onSubmit={handleSubmit(onSubmit)} sx={{ width: '100%' }}>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <TextField
          {...register('tenantName')}
          fullWidth
          label="租户名称"
          variant="outlined"
          margin="normal"
          error={!!errors.tenantName}
          helperText={errors.tenantName?.message}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Business color="action" />
              </InputAdornment>
            ),
          }}
          disabled={isSubmitting || isLoading}
        />

        <TextField
          {...register('username')}
          fullWidth
          label="用户名"
          variant="outlined"
          margin="normal"
          error={!!errors.username}
          helperText={errors.username?.message}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Person color="action" />
              </InputAdornment>
            ),
          }}
          disabled={isSubmitting || isLoading}
        />

        <TextField
          {...register('password')}
          fullWidth
          label="密码"
          type={showPassword ? 'text' : 'password'}
          variant="outlined"
          margin="normal"
          error={!!errors.password}
          helperText={errors.password?.message}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Lock color="action" />
              </InputAdornment>
            ),
            endAdornment: (
              <InputAdornment position="end">
                <IconButton
                  aria-label="toggle password visibility"
                  onClick={handleTogglePasswordVisibility}
                  edge="end"
                  disabled={isSubmitting || isLoading}
                >
                  {showPassword ? <VisibilityOff /> : <Visibility />}
                </IconButton>
              </InputAdornment>
            ),
          }}
          disabled={isSubmitting || isLoading}
        />

        <Button
          type="submit"
          fullWidth
          variant="contained"
          size="large"
          sx={{ mt: 3, mb: 2, py: 1.5 }}
          disabled={isSubmitting || isLoading}
          startIcon={
            isSubmitting || isLoading ? (
              <CircularProgress size={20} color="inherit" />
            ) : null
          }
        >
          {isSubmitting || isLoading ? '登录中...' : '登录'}
        </Button>

        <Box sx={{ textAlign: 'center', mt: 2 }}>
          <Typography variant="body2" color="text.secondary">
            忘记密码？请联系管理员
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
}
