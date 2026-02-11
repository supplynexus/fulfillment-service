'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowBack as ArrowBackIcon,
  DataObject as DataObjectIcon,
  Link as LinkIcon,
  OpenInNew as OpenInNewIcon,
  Refresh as RefreshIcon,
  Sync as SyncIcon,
  CompareArrows as CompareArrowsIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Article as ArticleIcon,
} from '@mui/icons-material';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import useEmblaCarousel from 'embla-carousel-react';
import DOMPurify from 'dompurify';
import { useParams, useRouter } from 'next/navigation';
import toast from 'react-hot-toast';

import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { JsonViewerDialog } from '@/components/common/JsonViewerDialog';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { ProductMappingDialog } from '@/components/printify/ProductMappingDialog';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';

interface PrintifyProduct {
  id: string;
  title: string;
  description?: string;
  tags: string[];
  variants: Array<{
    id: number;
    sku: string;
    price: number;
    title: string;
    is_enabled: boolean;
    is_available: boolean;
  }>;
  images: Array<{
    src: string;
    is_default: boolean;
  }>;
  updated_at?: string;
  is_published?: boolean;
}

interface CompareWithLocalResult {
  success: boolean;
  is_in_sync: boolean;
  remote?: { updated_at?: string };
  local?: {
    raw_data_updated_at?: string;
    last_synced_at?: string;
    updated_at?: string;
    is_published?: boolean;
  };
}

function PrintifyProductDetailPage() {
  const router = useRouter();
  const params = useParams<{ external_system_hashid: string; productId: string }>();
  const externalSystemHashid = params?.external_system_hashid;
  const productId = params?.productId;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [product, setProduct] = useState<PrintifyProduct | null>(null);
  const [productJson, setProductJson] = useState<unknown>(null);

  const [openJsonDialog, setOpenJsonDialog] = useState(false);
  const [loadingProductJson, setLoadingProductJson] = useState(false);
  const [openMappingDialog, setOpenMappingDialog] = useState(false);
  const [openHtmlDialog, setOpenHtmlDialog] = useState(false);
  const [openCompareDialog, setOpenCompareDialog] = useState(false);
  const [compareResult, setCompareResult] = useState<CompareWithLocalResult | null>(
    null
  );
  const [comparingWithLocal, setComparingWithLocal] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const [emblaRef, emblaApi] = useEmblaCarousel({ loop: true });
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);

  const getPrintifyProductUrl = (id: string) =>
    `https://printify.com/app/product-details/${id}?fromProductsPage=1`;

  const htmlToText = (html?: string) => {
    if (!html) return '';
    return html
      .replace(/<[^>]+>/g, ' ')
      .replace(/&nbsp;/gi, ' ')
      .replace(/&amp;/gi, '&')
      .replace(/&quot;/gi, '"')
      .replace(/&#39;/gi, "'")
      .replace(/\s+/g, ' ')
      .trim();
  };

  const sanitizeHtml = (html?: string) => {
    if (!html) return '';
    return DOMPurify.sanitize(html, {
      USE_PROFILES: { html: true },
      FORBID_TAGS: ['script', 'iframe', 'object', 'embed'],
      FORBID_ATTR: ['onerror', 'onclick', 'onload', 'style'],
    });
  };

  const loadProduct = useCallback(async () => {
    if (!externalSystemHashid || !productId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await frontendApi.get(
        `/api/external-systems/printify/${externalSystemHashid}/products/${productId}/json`
      );
      const latestProduct = response.data?.product as PrintifyProduct | undefined;
      if (!latestProduct) {
        throw new Error('未获取到商品详情');
      }
      setProduct(latestProduct);
      setProductJson(latestProduct);
    } catch (e) {
      frontendLogger.error('❌ 获取 Printify 商品详情失败', {
        error: String(e),
        externalSystemHashid,
        productId,
      });
      setError('获取商品详情失败');
    } finally {
      setLoading(false);
    }
  }, [externalSystemHashid, productId]);

  useEffect(() => {
    loadProduct();
  }, [loadProduct]);

  useEffect(() => {
    if (!emblaApi) return;
    const onSelect = () => setSelectedImageIndex(emblaApi.selectedScrollSnap());
    emblaApi.on('select', onSelect);
    onSelect();
    return () => emblaApi.off('select', onSelect);
  }, [emblaApi]);

  const selectedProductImages = useMemo(() => {
    if (!product) return [];
    return product.images?.length
      ? product.images
      : [{ src: '/placeholder-product.png', is_default: true }];
  }, [product]);

  const enabledVariants = useMemo(
    () => product?.variants?.filter(v => v.is_enabled) || [],
    [product]
  );

  const getProductPriceRange = (p: PrintifyProduct) => {
    const prices = p.variants.map(v => v.price / 100).filter(v => v > 0);
    if (prices.length === 0) return 'N/A';
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    return min === max
      ? `$${min.toFixed(2)}`
      : `$${min.toFixed(2)} - $${max.toFixed(2)}`;
  };

  const handleCompareWithLocal = useCallback(async () => {
    if (!externalSystemHashid || !product) return;
    try {
      setComparingWithLocal(true);
      const response = await frontendApi.get(
        `/api/external-systems/printify/${externalSystemHashid}/products/${product.id}/compare-local`
      );
      setCompareResult(response.data as CompareWithLocalResult);
      setOpenCompareDialog(true);
    } catch (e: any) {
      toast.error(e?.response?.data?.error || '比较本地数据失败');
    } finally {
      setComparingWithLocal(false);
    }
  }, [externalSystemHashid, product]);

  const handleRefreshJson = useCallback(
    async (openAfter = false) => {
      if (!externalSystemHashid || !product) return;
      try {
        setLoadingProductJson(true);
        const response = await frontendApi.get(
          `/api/external-systems/printify/${externalSystemHashid}/products/${product.id}/json`
        );
        const latestProduct = response.data?.product as PrintifyProduct | undefined;
        if (latestProduct) {
          setProduct(latestProduct);
          setProductJson(latestProduct);
        }
        if (openAfter) setOpenJsonDialog(true);
      } catch (e: any) {
        toast.error(e?.response?.data?.error || '读取商品 JSON 失败');
      } finally {
        setLoadingProductJson(false);
      }
    },
    [externalSystemHashid, product]
  );

  const handleSyncProduct = useCallback(async () => {
    if (!externalSystemHashid || !product) return;
    try {
      setSyncing(true);
      toast.loading('正在同步该商品到本地…', { id: 'printify-single-sync' });
      await frontendApi.post('/api/printify-sync/sync-products', {
        external_system_id_hashid: externalSystemHashid,
        product_ids: [product.id],
      });
      toast.success('同步成功', { id: 'printify-single-sync' });
      await loadProduct();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || '同步失败', {
        id: 'printify-single-sync',
      });
    } finally {
      setSyncing(false);
    }
  }, [externalSystemHashid, product, loadProduct]);

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Box sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Button
              variant='outlined'
              startIcon={<ArrowBackIcon />}
              onClick={() => router.push('/external-systems/printify/products')}
            >
              返回实时商品列表
            </Button>
            <Button
              variant='outlined'
              startIcon={<RefreshIcon />}
              onClick={loadProduct}
              disabled={loading}
            >
              刷新详情
            </Button>
          </Box>

          {loading ? (
            <Box sx={{ py: 6, display: 'flex', justifyContent: 'center' }}>
              <CircularProgress />
            </Box>
          ) : error ? (
            <Alert severity='error'>{error}</Alert>
          ) : product ? (
            <>
              <Typography variant='h4' component='h1' gutterBottom>
                {product.title}
              </Typography>
              <Typography variant='body2' color='text.secondary' sx={{ mb: 2 }}>
                Printify Product ID: {product.id}
              </Typography>

              <Card sx={{ mb: 2 }}>
                <CardContent>
                  <Box
                    sx={{
                      position: 'relative',
                      borderRadius: 2,
                      overflow: 'hidden',
                      border: '1px solid',
                      borderColor: 'divider',
                      backgroundColor: '#fafafa',
                      mb: 1,
                    }}
                  >
                    <Box ref={emblaRef} sx={{ overflow: 'hidden' }}>
                      <Box sx={{ display: 'flex' }}>
                        {selectedProductImages.map((img, index) => (
                          <Box
                            key={`${img.src}-${index}`}
                            sx={{
                              flex: '0 0 100%',
                              minWidth: 0,
                              display: 'flex',
                              justifyContent: 'center',
                              alignItems: 'center',
                              py: 2,
                            }}
                          >
                            <img
                              src={img.src}
                              alt={`${product.title}-${index + 1}`}
                              style={{
                                maxWidth: '100%',
                                maxHeight: '360px',
                                objectFit: 'contain',
                              }}
                            />
                          </Box>
                        ))}
                      </Box>
                    </Box>
                    <Button
                      size='small'
                      variant='contained'
                      onClick={() => emblaApi?.scrollPrev()}
                      sx={{
                        minWidth: 0,
                        position: 'absolute',
                        top: '50%',
                        left: 8,
                        transform: 'translateY(-50%)',
                      }}
                    >
                      <ChevronLeftIcon />
                    </Button>
                    <Button
                      size='small'
                      variant='contained'
                      onClick={() => emblaApi?.scrollNext()}
                      sx={{
                        minWidth: 0,
                        position: 'absolute',
                        top: '50%',
                        right: 8,
                        transform: 'translateY(-50%)',
                      }}
                    >
                      <ChevronRightIcon />
                    </Button>
                  </Box>
                  <Typography
                    variant='caption'
                    color='text.secondary'
                    sx={{ display: 'block', textAlign: 'center' }}
                  >
                    图片 {selectedImageIndex + 1} / {selectedProductImages.length || 1}
                  </Typography>
                </CardContent>
              </Card>

              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
                  gap: 2,
                }}
              >
                <Card>
                  <CardContent>
                    <Typography variant='h6' gutterBottom>
                      基本信息
                    </Typography>
                    <Typography variant='body2' color='text.secondary' paragraph>
                      {htmlToText(product.description) || '暂无描述'}
                    </Typography>
                    <Button
                      size='small'
                      variant='outlined'
                      startIcon={<ArticleIcon />}
                      onClick={() => setOpenHtmlDialog(true)}
                      disabled={!product.description}
                      sx={{ mb: 1 }}
                    >
                      预览 HTML 效果（已安全过滤）
                    </Button>
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1 }}>
                      {product.tags?.map((tag, index) => (
                        <Chip key={index} label={tag} size='small' />
                      ))}
                    </Box>
                    <Typography variant='body2'>
                      价格范围：<strong>{getProductPriceRange(product)}</strong>
                    </Typography>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent>
                    <Typography variant='h6' gutterBottom>
                      变体信息
                    </Typography>
                    <TableContainer component={Paper} variant='outlined' sx={{ maxHeight: 360 }}>
                      <Table size='small'>
                        <TableHead>
                          <TableRow>
                            <TableCell>变体规格</TableCell>
                            <TableCell>价格</TableCell>
                            <TableCell>库存</TableCell>
                            <TableCell>状态</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {enabledVariants.map(variant => (
                            <TableRow key={variant.id}>
                              <TableCell>{variant.title || `Variant #${variant.id}`}</TableCell>
                              <TableCell>${(variant.price / 100).toFixed(2)}</TableCell>
                              <TableCell>
                                <Chip
                                  label={variant.is_available ? '有库存' : '缺货'}
                                  color={variant.is_available ? 'success' : 'warning'}
                                  size='small'
                                />
                              </TableCell>
                              <TableCell>
                                <Chip label='启用' color='success' size='small' />
                              </TableCell>
                            </TableRow>
                          ))}
                          {enabledVariants.length === 0 && (
                            <TableRow>
                              <TableCell colSpan={4} align='center'>
                                暂无启用的变体
                              </TableCell>
                            </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </CardContent>
                </Card>
              </Box>

              <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Button
                  variant='outlined'
                  startIcon={<OpenInNewIcon />}
                  onClick={() =>
                    window.open(getPrintifyProductUrl(product.id), '_blank', 'noopener,noreferrer')
                  }
                >
                  打开 Printify 商品页
                </Button>
                <Button
                  variant='outlined'
                  startIcon={
                    loadingProductJson ? (
                      <CircularProgress size={16} color='inherit' />
                    ) : (
                      <RefreshIcon />
                    )
                  }
                  onClick={() => handleRefreshJson(false)}
                  disabled={loadingProductJson}
                >
                  重新读取商品 JSON
                </Button>
                <Button
                  variant='outlined'
                  startIcon={<DataObjectIcon />}
                  onClick={() => handleRefreshJson(true)}
                  disabled={loadingProductJson}
                >
                  查看 JSON
                </Button>
                <Button
                  variant='outlined'
                  startIcon={
                    comparingWithLocal ? (
                      <CircularProgress size={16} color='inherit' />
                    ) : (
                      <CompareArrowsIcon />
                    )
                  }
                  onClick={handleCompareWithLocal}
                  disabled={comparingWithLocal}
                >
                  与本地数据库比较
                </Button>
                <Button
                  variant='outlined'
                  startIcon={
                    syncing ? <CircularProgress size={16} color='inherit' /> : <SyncIcon />
                  }
                  onClick={handleSyncProduct}
                  disabled={syncing}
                >
                  同步到本地
                </Button>
                <Button
                  variant='outlined'
                  startIcon={<LinkIcon />}
                  onClick={() => setOpenMappingDialog(true)}
                >
                  映射到核心商品
                </Button>
              </Box>
            </>
          ) : null}

          <ProductMappingDialog
            open={openMappingDialog}
            onClose={() => setOpenMappingDialog(false)}
            printifyProduct={product}
            onMappingCreated={() => setOpenMappingDialog(false)}
          />

          <Dialog
            open={openHtmlDialog}
            onClose={() => setOpenHtmlDialog(false)}
            maxWidth='md'
            fullWidth
          >
            <DialogTitle>HTML 预览（安全过滤）</DialogTitle>
            <DialogContent>
              <Box
                sx={{
                  mt: 1,
                  p: 2,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  maxHeight: '70vh',
                  overflow: 'auto',
                }}
                dangerouslySetInnerHTML={{ __html: sanitizeHtml(product?.description) }}
              />
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setOpenHtmlDialog(false)}>关闭</Button>
            </DialogActions>
          </Dialog>

          <Dialog
            open={openCompareDialog}
            onClose={() => setOpenCompareDialog(false)}
            maxWidth='sm'
            fullWidth
          >
            <DialogTitle>与本地数据库比较</DialogTitle>
            <DialogContent>
              {compareResult ? (
                <Box sx={{ mt: 1, display: 'grid', gap: 1.5 }}>
                  <Alert severity={compareResult.is_in_sync ? 'success' : 'warning'}>
                    {compareResult.is_in_sync
                      ? '远程 Printify 与本地快照一致'
                      : '远程 Printify 与本地快照不一致'}
                  </Alert>
                  <Typography variant='body2'>
                    <strong>远程 updated_at:</strong> {compareResult.remote?.updated_at || '-'}
                  </Typography>
                  <Typography variant='body2'>
                    <strong>本地 raw_data.updated_at:</strong>{' '}
                    {compareResult.local?.raw_data_updated_at || '-'}
                  </Typography>
                  <Typography variant='body2'>
                    <strong>本地 last_synced_at:</strong>{' '}
                    {compareResult.local?.last_synced_at || '-'}
                  </Typography>
                  <Typography variant='body2'>
                    <strong>本地 DB updated_at:</strong> {compareResult.local?.updated_at || '-'}
                  </Typography>
                  <Typography variant='body2'>
                    <strong>本地发布状态:</strong>{' '}
                    {compareResult.local?.is_published ? '已发布' : '未发布'}
                  </Typography>
                </Box>
              ) : (
                <Box sx={{ py: 3, textAlign: 'center' }}>
                  <CircularProgress size={24} />
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setOpenCompareDialog(false)}>关闭</Button>
            </DialogActions>
          </Dialog>

          <JsonViewerDialog
            open={openJsonDialog}
            onClose={() => setOpenJsonDialog(false)}
            title='Printify 商品 JSON'
            subtitle={product?.title}
            data={productJson}
            loading={loadingProductJson}
          />
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
}

export default PrintifyProductDetailPage;
