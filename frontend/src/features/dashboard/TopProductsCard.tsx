import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { QueryState } from "@/components/common/QueryState";
import { getTopProducts } from "@/features/dashboard/api";
import { formatCurrency } from "@/lib/format";

export function TopProductsCard() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["analytics", "products"],
    queryFn: () => getTopProducts(5),
  });

  return (
    <Card>
      <h2 className="text-sm font-semibold text-slate-200">Top Products</h2>
      <div className="mt-4">
        <QueryState
          isLoading={isLoading}
          isError={isError}
          error={error}
          isEmpty={!isLoading && !isError && (data?.products.length ?? 0) === 0}
          emptyMessage="No product sales in this range yet."
        >
          <ul className="divide-y divide-slate-800">
            {data?.products.map((product) => (
              <li key={product.product_id} className="flex items-center justify-between py-2 text-sm">
                <div>
                  <p className="text-slate-200">{product.name}</p>
                  <p className="text-xs text-slate-500">{product.category}</p>
                </div>
                <div className="text-right">
                  <p className="text-slate-200">{formatCurrency(product.revenue)}</p>
                  <p className="text-xs text-slate-500">{product.quantity_sold} sold</p>
                </div>
              </li>
            ))}
          </ul>
        </QueryState>
      </div>
    </Card>
  );
}
