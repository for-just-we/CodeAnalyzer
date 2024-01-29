
#define cast(t, exp)	((t)(exp))

typedef void * (*lua_Alloc) (void *ud, void *ptr, size_t osize, size_t nsize);

lua_State *lua_newstate (lua_Alloc f, void *ud) {
  int i;
  lua_State *L;
  global_State *g;
  cast(LG*, (*f)(ud, NULL, LUA_TTHREAD, sizeof(LG)));
}