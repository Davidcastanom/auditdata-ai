export class Store {
  constructor() {
    this.state = this.loadState() || {
      step: 0,
      filename: "",
      fileBase64: "",
      analysis: null,
      cleaning: null,
      actions: [],
    };
  }

  loadState() {
    try {
      const data = localStorage.getItem("auditdata_state");
      return data ? JSON.parse(data) : null;
    } catch (e) {
      console.error("Error loading state", e);
      return null;
    }
  }

  saveState() {
    try {
      localStorage.setItem("auditdata_state", JSON.stringify(this.state));
    } catch (e) {
      console.error("Error saving state", e);
    }
  }

  clear() {
    this.state = {
      step: 0,
      filename: "",
      fileBase64: "",
      analysis: null,
      cleaning: null,
      actions: [],
    };
    this.saveState();
  }

  setFile(filename, fileBase64) {
    this.state.filename = filename;
    this.state.fileBase64 = fileBase64;
    this.state.analysis = null;
    this.state.cleaning = null;
    this.state.actions = [];
    this.saveState();
  }

  setAnalysis(analysis) {
    this.state.analysis = analysis;
    this.state.cleaning = null;
    this.state.actions = [];
    this.saveState();
  }

  setCleaning(cleaning) {
    this.state.cleaning = cleaning;
    this.saveState();
  }

  addAction(action) {
    this.state.actions.push(action);
    this.saveState();
  }

  removeAction(index) {
    if (index >= 0 && index < this.state.actions.length) {
      const removed = this.state.actions.splice(index, 1)[0];
      this.saveState();
      return removed;
    }
    return null;
  }

  undoAction() {
    return this.removeAction(this.state.actions.length - 1);
  }

  setStep(step) {
    this.state.step = step;
    this.saveState();
  }
}
