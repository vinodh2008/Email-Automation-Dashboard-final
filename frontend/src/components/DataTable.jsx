import { Pagination } from './Pagination';

export const DataTable = ({ 
  columns, 
  data, 
  keyField = 'id',
  page, 
  pageSize, 
  total, 
  onPageChange,
  onPageSizeChange,
  emptyState,
  loading,
  loadingSkeleton
}) => {
  if (loading && loadingSkeleton) return loadingSkeleton;
  if (!data || data.length === 0) return emptyState || <div className="p-8 text-center text-on-surface-variant text-body-md">No data available</div>;

  return (
    <div className="flex flex-col w-full">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-outline-variant">
          <thead className="bg-[#F6F8FA]">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.header || col.accessor || `col-${idx}`}
                  scope="col"
                  className={`px-6 py-3 text-left text-label-bold uppercase tracking-wider text-on-surface-variant ${col.className || ''}`}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-surface divide-y divide-outline-variant">
            {data.map((row) => (
              <tr key={row[keyField]} className="hover:bg-surface-container-low transition-colors">
              {columns.map((col, idx) => (
                  <td key={col.header || col.accessor} className={`px-6 py-4 whitespace-nowrap text-body-md text-on-surface ${col.cellClassName || ''}`}>
                    {col.render ? col.render(row) : row[col.accessor]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {(total !== undefined && page && pageSize && onPageChange) && (
        <Pagination total={total} page={page} pageSize={pageSize} onPageChange={onPageChange} onPageSizeChange={onPageSizeChange} />
      )}
    </div>
  );
};
