import { useAuthContext } from '../context/AuthContext';

export const useAuth = () => {
  const ctx = useAuthContext();
  return {
    ...ctx,
    isAuthenticated: Boolean(ctx.token),
  };
};
