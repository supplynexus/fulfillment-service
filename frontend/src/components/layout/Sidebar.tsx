'use client';

import React, { useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Collapse,
  Box,
  Typography,
  Divider,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  ShoppingCart as OrdersIcon,
  Inventory as ProductsIcon,
  LocalShipping as ScmOrdersIcon,
  Settings as SettingsIcon,
  AccountCircle as ProfileIcon,
  ExpandLess,
  ExpandMore,
  Menu as MenuIcon,
  ChevronLeft as ChevronLeftIcon,
} from '@mui/icons-material';

interface SidebarProps {
  open: boolean;
  onToggle: () => void;
}

interface MenuItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path?: string;
  children?: MenuItem[];
}

const menuItems: MenuItem[] = [
  {
    id: 'dashboard',
    label: '仪表板',
    icon: <DashboardIcon />,
    path: '/dashboard',
  },
  {
    id: 'orders',
    label: '订单管理',
    icon: <OrdersIcon />,
    children: [
      {
        id: 'orders-list',
        label: '订单列表',
        icon: <OrdersIcon />,
        path: '/orders',
      },
      {
        id: 'scm-orders',
        label: 'SCM 订单',
        icon: <ScmOrdersIcon />,
        path: '/scm-orders',
      },
    ],
  },
  {
    id: 'products',
    label: '商品管理',
    icon: <ProductsIcon />,
    children: [
      {
        id: 'products-list',
        label: '商品列表',
        icon: <ProductsIcon />,
        path: '/products',
      },
      {
        id: 'product-sync',
        label: '商品同步',
        icon: <ProductsIcon />,
        path: '/products/sync',
      },
    ],
  },
  {
    id: 'settings',
    label: '系统设置',
    icon: <SettingsIcon />,
    children: [
      {
        id: 'profile',
        label: '个人资料',
        icon: <ProfileIcon />,
        path: '/settings/profile',
      },
      {
        id: 'system-settings',
        label: '系统设置',
        icon: <SettingsIcon />,
        path: '/settings',
      },
    ],
  },
];

const DRAWER_WIDTH = 280;
const DRAWER_WIDTH_COLLAPSED = 64;

export function Sidebar({ open, onToggle }: SidebarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [expandedItems, setExpandedItems] = useState<string[]>([
    'orders',
    'products',
    'settings',
  ]);

  const handleItemClick = (item: MenuItem) => {
    if (item.path) {
      router.push(item.path);
    } else if (item.children) {
      // Toggle expansion
      setExpandedItems(prev =>
        prev.includes(item.id)
          ? prev.filter(id => id !== item.id)
          : [...prev, item.id]
      );
    }
  };

  const isItemActive = (item: MenuItem): boolean => {
    if (item.path) {
      return pathname === item.path;
    }
    if (item.children) {
      return item.children.some(child => child.path === pathname);
    }
    return false;
  };

  const renderMenuItem = (item: MenuItem, level: number = 0) => {
    const isActive = isItemActive(item);
    const isExpanded = expandedItems.includes(item.id);
    const hasChildren = item.children && item.children.length > 0;

    return (
      <React.Fragment key={item.id}>
        <ListItem disablePadding>
          <ListItemButton
            onClick={() => handleItemClick(item)}
            sx={{
              pl: 2 + level * 2,
              pr: 2,
              py: 1,
              minHeight: 48,
              backgroundColor: isActive ? 'primary.light' : 'transparent',
              color: isActive ? 'primary.contrastText' : 'inherit',
              '&:hover': {
                backgroundColor: isActive ? 'primary.light' : 'action.hover',
              },
              borderRadius: 1,
              mx: 1,
              my: 0.5,
            }}
          >
            <ListItemIcon
              sx={{
                minWidth: 40,
                color: isActive ? 'primary.contrastText' : 'inherit',
              }}
            >
              {item.icon}
            </ListItemIcon>
            {open && (
              <>
                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{
                    fontSize: '0.875rem',
                    fontWeight: isActive ? 600 : 400,
                  }}
                />
                {hasChildren && (
                  <Box>{isExpanded ? <ExpandLess /> : <ExpandMore />}</Box>
                )}
              </>
            )}
          </ListItemButton>
        </ListItem>

        {hasChildren && open && (
          <Collapse in={isExpanded} timeout='auto' unmountOnExit>
            <List component='div' disablePadding>
              {item.children!.map(child => renderMenuItem(child, level + 1))}
            </List>
          </Collapse>
        )}
      </React.Fragment>
    );
  };

  return (
    <Drawer
      variant='permanent'
      sx={{
        width: open ? DRAWER_WIDTH : DRAWER_WIDTH_COLLAPSED,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: open ? DRAWER_WIDTH : DRAWER_WIDTH_COLLAPSED,
          boxSizing: 'border-box',
          transition: 'width 0.3s ease',
          overflowX: 'hidden',
          borderRight: '1px solid',
          borderColor: 'divider',
          backgroundColor: 'background.paper',
        },
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: open ? 'space-between' : 'center',
          p: 2,
          minHeight: 64,
          borderBottom: '1px solid',
          borderColor: 'divider',
        }}
      >
        {open && (
          <Typography variant='h6' component='div' sx={{ fontWeight: 600 }}>
            SupplyNexus
          </Typography>
        )}
        <Tooltip title={open ? '收起菜单' : '展开菜单'}>
          <IconButton onClick={onToggle} size='small'>
            {open ? <ChevronLeftIcon /> : <MenuIcon />}
          </IconButton>
        </Tooltip>
      </Box>

      <Divider />

      {/* Menu Items */}
      <List sx={{ px: 1, py: 2 }}>
        {menuItems.map(item => renderMenuItem(item))}
      </List>
    </Drawer>
  );
}
