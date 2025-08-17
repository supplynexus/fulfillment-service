'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Menu,
  MenuItem,
  Avatar,
  Box,
  Divider,
} from '@mui/material';
import {
  AccountCircle,
  Logout,
  Settings,
  Dashboard,
} from '@mui/icons-material';
import { useAuth } from '@/lib/auth-context';
import { tokenManager } from '@/lib/auth';
import toast from 'react-hot-toast';

export function Header() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = async () => {
    try {
      await logout();
      toast.success('已成功退出登录');
      router.push('/auth/login');
    } catch (error) {
      console.error('Logout error:', error);
      toast.error('退出登录失败');
    }
    handleClose();
  };

  const handleProfile = () => {
    router.push('/settings/profile');
    handleClose();
  };

  const handleSettings = () => {
    router.push('/settings');
    handleClose();
  };

  const handleDashboard = () => {
    router.push('/dashboard');
    handleClose();
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <AppBar position='static' elevation={1}>
      <Toolbar>
        <Typography
          variant='h6'
          component='div'
          sx={{ flexGrow: 1, cursor: 'pointer' }}
          onClick={() => router.push('/dashboard')}
        >
          SupplyNexus
        </Typography>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {/* 用户信息 */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant='body2' color='inherit'>
              {user?.full_name || user?.email || '用户'}
            </Typography>
          </Box>

          {/* 用户菜单 */}
          <IconButton
            size='large'
            aria-label='用户菜单'
            aria-controls='menu-appbar'
            aria-haspopup='true'
            onClick={handleMenu}
            color='inherit'
          >
            <Avatar
              sx={{
                width: 32,
                height: 32,
                bgcolor: 'primary.dark',
                fontSize: '0.875rem',
              }}
            >
              {user?.full_name ? getInitials(user.full_name) : 'U'}
            </Avatar>
          </IconButton>

          <Menu
            id='menu-appbar'
            anchorEl={anchorEl}
            anchorOrigin={{
              vertical: 'bottom',
              horizontal: 'right',
            }}
            keepMounted
            transformOrigin={{
              vertical: 'top',
              horizontal: 'right',
            }}
            open={Boolean(anchorEl)}
            onClose={handleClose}
            PaperProps={{
              sx: {
                mt: 1,
                minWidth: 200,
              },
            }}
          >
            <MenuItem onClick={handleDashboard}>
              <Dashboard sx={{ mr: 2, fontSize: 20 }} />
              仪表板
            </MenuItem>

            <MenuItem onClick={handleProfile}>
              <AccountCircle sx={{ mr: 2, fontSize: 20 }} />
              个人资料
            </MenuItem>

            <MenuItem onClick={handleSettings}>
              <Settings sx={{ mr: 2, fontSize: 20 }} />
              设置
            </MenuItem>

            <Divider />

            <MenuItem onClick={handleLogout} sx={{ color: 'error.main' }}>
              <Logout sx={{ mr: 2, fontSize: 20 }} />
              退出登录
            </MenuItem>
          </Menu>
        </Box>
      </Toolbar>
    </AppBar>
  );
}
