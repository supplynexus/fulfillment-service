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
  Visibility as ViewIcon,
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
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';

import { JsonViewerDialog } from '@/components/common/JsonViewerDialog';
import { ProductMappingDialog } from '@/components/printify/ProductMappingDialog';
import { frontendApi } from '@/lib/api';
import { frontendLogger } from '@/lib/frontend-logger';

/** Normalized Printify product shape for list + detail (list has price/cost, detail /json has price) */
export interface PrintifyProductDetailShape {
  id: string;
  title: string;
  description?: string;
  tags: string[];
  variants: Array<{
    id: number;
    sku: string;
    price?: number;
    cost?: number;
    title: string;
    is_enabled: boolean;
    is_available: boolean;
  }>;
  images: Array<{
    src: string;
    is_default?: boolean;
    variant_ids?: number[];
    position?: string;
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

export type PrintifyProductDetailVariant = 'dialog' | 'page';

export interface PrintifyProductDetailViewProps {
  variant: PrintifyProductDetailVariant;
  /** When variant=dialog: pass product + externalSystemHashid. When variant=page: can pass product (e.g. from SSR) or leave undefined to fetch by productId. */
  product?: PrintifyProductDetailShape | null;
  externalSystemHashid: string | null;
  /** Required when variant=page and product is not provided (fetch by id). */
  productId?: string | null;
  onClose?: () => void;
  /** When variant=dialog, optional: called when product is refreshed (e.g. after JSON reload) so list can update. */
  onProductUpdated?: (product: PrintifyProductDetailShape) => void;
  /** When variant=dialog: base path for "open in new page" link (e.g. list path). */
  listPath?: string;
}

function getPrintifyProductUrl(id: string) {
  return `https://printify.com/app/product-details/${id}?fromProductsPage=1`;
}

function htmlToText(html?: string) {
  if (!html) return '';
  return html
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/\s+/g, ' ')
    .trim();
}

function sanitizeHtml(html?: string) {
  if (!html) return '';
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['script', 'iframe', 'object', 'embed'],
    FORBID_ATTR: ['onerror', 'onclick', 'onload', 'style'],
  });
}

function getProductPriceRange(p: PrintifyProductDetailShape) {
  const prices = (p.variants || [])
    .map(v => ((v.price ?? v.cost ?? 0) / 100))
    .filter(x => x > 0);
  if (prices.length === 0) return 'N/A';
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  return min === max
    ? `$${min.toFixed(2)}`
    : `$${min.toFixed(2)} - $${max.toFixed(2)}`;
}

export function PrintifyProductDetailView({
  variant,
  product: productProp,
  externalSystemHashid,
  productId: productIdProp,
  onClose,
  onProductUpdated,
  listPath = '/external-systems/printify/products',
}: PrintifyProductDetailViewProps) {
  const router = useRouter();
  const isPage = variant === 'page';
  const idFromProp = productIdProp ?? productProp?.id ?? null;

  const [product, setProduct] = useState<PrintifyProductDetailShape | null>(
    productProp ?? null
  );
  const [loading, setLoading] = useState(isPage && !productProp && !!idFromProp);
  const [error, setError] = useState<string | null>(null);
  const [productJson, setProductJson] = useState<unknown>(null);
  const [openJsonDialog, setOpenJsonDialog] = useState(false);
  const [loadingProductJson, setLoadingProductJson] = useState(false);
  const [openMappingDialog, setOpenMappingDialog] = useState(false);
  const [openHtmlDialog, setOpenHtmlDialog] = useState(false);
  const [openCompareDialog, setOpenCompareDialog] = useState(false);
  const [compareResult, setCompareResult] =
    useState<CompareWithLocalResult | null>(null);
  const [comparingWithLocal, setComparingWithLocal] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [emblaRef, emblaApi] = useEmblaCarousel({ loop: true });
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);

  const effectiveProduct = productProp ?? product;
  const effectiveId = idFromProp ?? effectiveProduct?.id;

  const loadProduct = useCallback(async () => {
    if (!externalSystemHashid || !effectiveId) return;
    setLoading(true);
    setError(null);
    try {
      frontendLogger.info('PrintifyProductDetailView load product', {
        externalSystemHashid,
        productId: effectiveId,
        variant,
      });
      const response = await frontendApi.get(
        `/api/external-systems/printify/${externalSystemHashid}/products/${effectiveId}/json`
      );
      const data = response.data?.product as PrintifyProductDetailShape | undefined;
      if (!data) {
        throw new Error('未获取到商品详情');
      }
      setProduct(data);
      setProductJson(data);
    } catch (e) {
      frontendLogger.error('PrintifyProductDetailView load product failed', {
        error: String(e),
        externalSystemHashid,
        productId: effectiveId,
      });
      setError('获取商品详情失败');
    } finally {
      setLoading(false);
    }
  }, [externalSystemHashid, effectiveId, variant]);

  // Sync productProp into local state when used as dialog
  useEffect(() => {
    if (productProp != null) {
      setProduct(productProp);
      setError(null);
    }
  }, [productProp]);

  // Page mode: fetch by productId when no product passed
  useEffect(() => {
    if (!isPage || productProp != null) return;
    if (!externalSystemHashid || !productIdProp) {
      setError('缺少店铺或商品 ID');
      setLoading(false);
      return;
    }
    loadProduct();
  }, [isPage, productProp, externalSystemHashid, productIdProp, loadProduct]);

  useEffect(() => {
    if (!emblaApi) return;
    const onSelect = () => setSelectedImageIndex(emblaApi.selectedScrollSnap());
    emblaApi.on('select', onSelect);
    onSelect();
    return () => emblaApi.off('select', onSelect);
  }, [emblaApi]);

  const selectedProductImages = useMemo(() => {
    if (!effectiveProduct) return [];
    if (effectiveProduct.images?.length) return effectiveProduct.images;
    const src =
      effectiveProduct.images?.[0]?.src ||
      '/placeholder-product.png';
    return [{ src, is_default: true }];
  }, [effectiveProduct]);

  const enabledVariants = useMemo(
    () =>
      (effectiveProduct?.variants ?? []).filter(v => v.is_enabled),
    [effectiveProduct]
  );

  const handleRefreshJson = useCallback(
    async (openAfter: boolean) => {
      if (!externalSystemHashid || !effectiveProduct) return;
      try {
        setLoadingProductJson(true);
        const response = await frontendApi.get(
          `/api/external-systems/printify/${externalSystemHashid}/products/${effectiveProduct.id}/json`
        );
        const latest = response.data?.product as PrintifyProductDetailShape | undefined;
        if (latest) {
          setProduct(latest);
          setProductJson(latest);
          onProductUpdated?.(latest);
        } else {
          setProductJson(response.data);
        }
        if (openAfter) setOpenJsonDialog(true);
      } catch (e: unknown) {
        frontendLogger.error('PrintifyProductDetailView refresh JSON failed', {
          error: String(e),
          productId: effectiveProduct.id,
        });
        toast.error(
          (e as { response?: { data?: { error?: string } } })?.response?.data
            ?.error || '读取商品 JSON 失败'
        );
      } finally {
        setLoadingProductJson(false);
      }
    },
    [externalSystemHashid, effectiveProduct, onProductUpdated]
  );

  const handleCompareWithLocal = useCallback(async () => {
    if (!externalSystemHashid || !effectiveProduct) return;
    try {
      setComparingWithLocal(true);
      const response = await frontendApi.get(
        `/api/external-systems/printify/${externalSystemHashid}/products/${effectiveProduct.id}/compare-local`
      );
      setCompareResult(response.data as CompareWithLocalResult);
      setOpenCompareDialog(true);
    } catch (e: unknown) {
      frontendLogger.error('PrintifyProductDetailView compare local failed', {
        error: String(e),
        productId: effectiveProduct.id,
      });
      toast.error(
        (e as { response?: { data?: { error?: string } } })?.response?.data
          ?.error || '比较本地数据失败'
      );
    } finally {
      setComparingWithLocal(false);
    }
  }, [externalSystemHashid, effectiveProduct]);

  const handleSyncProduct = useCallback(async () => {
    if (!externalSystemHashid || !effectiveProduct) return;
    try {
      setSyncing(true);
      toast.loading('正在同步该商品到本地…', { id: 'printify-single-sync' });
      frontendLogger.info('PrintifyProductDetailView sync product', {
        productId: effectiveProduct.id,
        externalSystemHashid,
      });
      await frontendApi.post('/api/printify-sync/sync-products', {
        external_system_id_hashid: externalSystemHashid,
        product_ids: [effectiveProduct.id],
      });
      toast.success(`同步成功：${effectiveProduct.title} 已写入本地`, {
        id: 'printify-single-sync',
      });
      if (isPage) loadProduct();
    } catch (e: unknown) {
      frontendLogger.error('PrintifyProductDetailView sync failed', {
        error: String(e),
        productId: effectiveProduct.id,
      });
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || '同步失败';
      toast.error(msg, { id: 'printify-single-sync' });
    } finally {
      setSyncing(false);
    }
  }, [externalSystemHashid, effectiveProduct, isPage, loadProduct]);

  const goToDetailPage = useCallback(() => {
    if (!externalSystemHashid || !effectiveProduct) return;
    const path = `/external-systems/printify/products/${externalSystemHashid}/${effectiveProduct.id}`;
    if (isPage) return;
    router.push(path);
    onClose?.();
  }, [externalSystemHashid, effectiveProduct, isPage, router, onClose]);

  const goBackToList = useCallback(() => {
    router.push(listPath);
  }, [router, listPath]);

  if (isPage && loading && !effectiveProduct) {
    return (
      <Box sx={{ py: 6, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (isPage && error && !effectiveProduct) {
    return <Alert severity='error'>{error}</Alert>;
  }

  const content = effectiveProduct ? (
    <>
      {isPage && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <Button
            variant='outlined'
            startIcon={<ArrowBackIcon />}
            onClick={goBackToList}
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
      )}

      {isPage && (
        <>
          <Typography variant='h4' component='h1' gutterBottom>
            {effectiveProduct.title}
          </Typography>
          <Typography variant='body2' color='text.secondary' sx={{ mb: 2 }}>
            Printify Product ID: {effectiveProduct.id}
          </Typography>
        </>
      )}

      <Box sx={{ mb: 2 }}>
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
                    px: isPage ? 0 : 1,
                  }}
                >
                  <img
                    src={img.src}
                    alt={`${effectiveProduct.title}-${index + 1}`}
                    style={{
                      maxWidth: '100%',
                      maxHeight: isPage ? 360 : 300,
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
      </Box>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
          gap: 2,
        }}
      >
        <Card sx={isPage ? {} : { boxShadow: 'none', bgcolor: 'transparent' }}>
          <CardContent sx={isPage ? {} : { pt: 0, '&:last-child': { pb: 0 } }}>
            <Typography variant='h6' gutterBottom>
              基本信息
            </Typography>
            <Typography
              variant='body2'
              color='text.secondary'
              paragraph
              sx={{
                maxHeight: isPage ? undefined : 260,
                overflow: 'auto',
              }}
            >
              {htmlToText(effectiveProduct.description) || '暂无描述'}
            </Typography>
            <Button
              size='small'
              variant='outlined'
              startIcon={<ArticleIcon />}
              onClick={() => setOpenHtmlDialog(true)}
              disabled={!effectiveProduct.description}
              sx={{ mb: 2 }}
            >
              预览 HTML 效果（已安全过滤）
            </Button>
            <Typography variant='subtitle2' gutterBottom>
              标签:
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
              {(effectiveProduct.tags || []).map((tag, index) => (
                <Chip key={index} label={tag} size='small' />
              ))}
            </Box>
            {isPage && (
              <Typography variant='body2'>
                价格范围：<strong>{getProductPriceRange(effectiveProduct)}</strong>
              </Typography>
            )}
          </CardContent>
        </Card>

        <Card sx={isPage ? {} : { boxShadow: 'none', bgcolor: 'transparent' }}>
          <CardContent sx={isPage ? {} : { pt: 0, '&:last-child': { pb: 0 } }}>
            <Typography variant='h6' gutterBottom>
              变体信息
            </Typography>
            <TableContainer
              component={Paper}
              variant='outlined'
              sx={{ maxHeight: isPage ? 360 : 320, overflow: 'auto' }}
            >
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
                  {enabledVariants.map(variantRow => (
                    <TableRow key={variantRow.id}>
                      <TableCell>
                        {variantRow.title || `Variant #${variantRow.id}`}
                      </TableCell>
                      <TableCell>
                        $
                        {(
                          (variantRow.price ?? variantRow.cost ?? 0) /
                          100
                        ).toFixed(2)}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={
                            variantRow.is_available ? '有库存' : '缺货'
                          }
                          color={
                            variantRow.is_available ? 'success' : 'warning'
                          }
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
            window.open(
              getPrintifyProductUrl(effectiveProduct.id),
              '_blank',
              'noopener,noreferrer'
            )
          }
        >
          打开 Printify 商品页
        </Button>
        {!isPage && (
          <Button
            variant='outlined'
            startIcon={<ViewIcon />}
            onClick={goToDetailPage}
            disabled={!externalSystemHashid}
          >
            打开系统详情页
          </Button>
        )}
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
          {loadingProductJson ? '读取中…' : '重新读取商品 JSON'}
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
          {comparingWithLocal ? '比较中…' : '与本地数据库比较'}
        </Button>
        <Button
          variant='outlined'
          startIcon={
            syncing ? (
              <CircularProgress size={16} color='inherit' />
            ) : (
              <SyncIcon />
            )
          }
          onClick={handleSyncProduct}
          disabled={syncing}
        >
          {syncing ? '同步中…' : '同步到本地'}
        </Button>
        <Button
          variant='outlined'
          startIcon={<LinkIcon />}
          onClick={() => setOpenMappingDialog(true)}
        >
          映射到核心商品
        </Button>
        {!isPage && onClose && (
          <Button onClick={onClose}>关闭</Button>
        )}
      </Box>
    </>
  ) : null;

  return (
    <>
      {content}

      <ProductMappingDialog
        open={openMappingDialog}
        onClose={() => setOpenMappingDialog(false)}
        printifyProduct={effectiveProduct ?? undefined}
        onMappingCreated={() => {
          setOpenMappingDialog(false);
        }}
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
            dangerouslySetInnerHTML={{
              __html: sanitizeHtml(effectiveProduct?.description),
            }}
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
              <Alert
                severity={compareResult.is_in_sync ? 'success' : 'warning'}
              >
                {compareResult.is_in_sync
                  ? '远程 Printify 与本地快照一致'
                  : '远程 Printify 与本地快照不一致'}
              </Alert>
              <Typography variant='body2'>
                <strong>远程 updated_at:</strong>{' '}
                {compareResult.remote?.updated_at || '-'}
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
                <strong>本地 DB updated_at:</strong>{' '}
                {compareResult.local?.updated_at || '-'}
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
        subtitle={effectiveProduct?.title}
        data={productJson}
        loading={loadingProductJson}
      />
    </>
  );
}
