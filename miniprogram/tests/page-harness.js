function replaceModule(modulePath, exports) {
  const original = require.cache[modulePath];
  require.cache[modulePath] = {
    id: modulePath,
    filename: modulePath,
    loaded: true,
    exports,
  };
  return () => {
    if (original) {
      require.cache[modulePath] = original;
      return;
    }
    delete require.cache[modulePath];
  };
}

function loadPage(pageModulePath, mockModules) {
  const previousPage = global.Page;
  let pageConfig = null;
  const restores = Object.entries(mockModules || {}).map(([modulePath, exports]) =>
    replaceModule(modulePath, exports),
  );
  global.Page = (config) => {
    pageConfig = config;
  };

  try {
    delete require.cache[pageModulePath];
    require(pageModulePath);
  } finally {
    restores.reverse().forEach((restore) => restore());
    if (typeof previousPage === 'undefined') {
      delete global.Page;
    } else {
      global.Page = previousPage;
    }
  }

  if (!pageConfig) {
    throw new Error('未捕获 Page 配置');
  }
  return pageConfig;
}

function createPageContext(pageConfig) {
  const context = {
    data: JSON.parse(JSON.stringify(pageConfig.data || {})),
    setData(nextState) {
      this.data = {
        ...this.data,
        ...nextState,
      };
    },
  };
  Object.keys(pageConfig).forEach((key) => {
    if (key === 'data') {
      return;
    }
    context[key] = pageConfig[key];
  });
  return context;
}

module.exports = {
  createPageContext,
  loadPage,
};
