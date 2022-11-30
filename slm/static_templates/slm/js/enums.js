if (typeof slm === 'undefined' || slm == null) { var slm = {}; }

class LogEntryType {
    {% for entry in LogEntryType %}
    static {{entry.name}} = new LogEntryType({{entry.value}}, '{{entry.label}}', '{{entry.css}}');{% endfor %}

    constructor(val, label, css) {
        this.val = val;
        this.label = label;
        this.css = css;
    }

    toString() {
        return this.label;
    }

    static get(val) {
        switch(val) {{% for entry in LogEntryType %}
            case {{entry.value}}:
                return LogEntryType.{{entry.name}};{% endfor %}
        }
    }
}

class SiteLogStatus {
    {% for status in SiteLogStatus %}
    static {{status.name}} = new SiteLogStatus({{status.value}}, '{{status.label}}', '{{status.css}}', '{{status.color}}');{% endfor %}

    constructor(val, label, css, color) {
        this.val = val;
        this.label = label;
        this.css = css;
        this.color = color;
    }

    toString() {
        return this.label;
    }

    merge(sibling) {
        if (sibling !== null && sibling.val < this.val) {
            return sibling;
        }
        return this;
    }

    set(child) {
        if (
            this === SiteLogStatus.PUBLISHED ||
            this === SiteLogStatus.UPDATED ||
            this === SiteLogStatus.EMPTY
        ) {
            return child;
        }
        return this.merge(child);
    }

    static get(val) {
        switch(val) {{% for status in SiteLogStatus %}
            case {{status.value}}:
                return SiteLogStatus.{{status.name}};{% endfor %}
        }
    }
}

class AlertLevel {
    {% for level in AlertLevel %}
    static {{level.name}} = new AlertLevel({{level.value}}, '{{level.label}}', '{{level.bootstrap}}');{% endfor %}

    constructor(val, label, bootstrap) {
        this.val = val;
        this.label = label;
        this.bootstrap = bootstrap;
    }

    toString() {
        return this.label;
    }

    static get(val) {
        switch(val) {{% for level in AlertLevel %}
            case {{level.value}}:
                return AlertLevel.{{level.name}};{% endfor %}
        }
    }
}

slm.LogEntryType = LogEntryType;
slm.SiteLogStatus = SiteLogStatus;
slm.AlertLevel = AlertLevel;
