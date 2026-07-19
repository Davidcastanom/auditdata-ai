export class Router {
  constructor(onRouteChanged) {
    this.onRouteChanged = onRouteChanged;
    this.routes = {
      '#/comprender': 0,
      '#/perfilar': 1,
      '#/reglas': 2,
      '#/depurar': 3,
      '#/validar': 4,
      '#/informe': 5
    };
    
    window.addEventListener('hashchange', () => this.handleHashChange());
  }

  init() {
    if (!window.location.hash || !this.routes[window.location.hash]) {
      window.location.hash = '#/comprender';
    } else {
      this.handleHashChange();
    }
  }

  handleHashChange() {
    const hash = window.location.hash;
    const step = this.routes[hash] !== undefined ? this.routes[hash] : 0;
    this.onRouteChanged(step);
  }

  navigate(step) {
    const hash = Object.keys(this.routes).find(key => this.routes[key] === step);
    if (hash) {
      window.location.hash = hash;
    }
  }
}
