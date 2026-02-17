import type { QueryClient, QueryKey } from "@tanstack/react-query"

export const invalidateQueryKeys = async (
  queryClient: QueryClient,
  queryKeys: QueryKey[],
) => {
  await Promise.all(
    queryKeys.map((queryKey) => queryClient.invalidateQueries({ queryKey })),
  )
}

export const invalidateAndRefetchActiveQueryKeys = async (
  queryClient: QueryClient,
  queryKeys: QueryKey[],
) => {
  await Promise.all([
    ...queryKeys.map((queryKey) => queryClient.invalidateQueries({ queryKey })),
    ...queryKeys.map((queryKey) =>
      queryClient.refetchQueries({ queryKey, type: "active" }),
    ),
  ])
}
