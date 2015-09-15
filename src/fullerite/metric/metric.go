package metric

import "strings"

// The different types of metrics that are supported
const (
	Gauge             = "gauge"
	Counter           = "counter"
	CumulativeCounter = "cumcounter"
)

// Metric type holds all the information for a single metric data
// point. Metrics are generated in collectors and passed to handlers.
type Metric struct {
	Name       string            `json:"name"`
	MetricType string            `json:"type"`
	Value      float64           `json:"value"`
	Dimensions map[string]string `json:"dimensions"`
}

// New returns a new metric with name. Default metric type is "gauge"
// and timestamp is set to now. Value is initialized to 0.0.
func New(name string) Metric {
	return Metric{
		Name:       sanitizeString(name),
		MetricType: "gauge",
		Value:      0.0,
		Dimensions: make(map[string]string),
	}
}

// AddDimension adds a new dimension to the Metric.
func (m *Metric) AddDimension(name, value string) {
	m.Dimensions[sanitizeString(name)] = sanitizeString(value)
}

// GetDimensions returns the dimensions of a metric merged with defaults. Defaults win.
func (m *Metric) GetDimensions(defaults map[string]string) (dimensions map[string]string) {
	dimensions = make(map[string]string)
	for name, value := range m.Dimensions {
		dimensions[name] = value
	}
	for name, value := range defaults {
		dimensions[name] = value
	}
	return dimensions
}

// GetDimensionValue returns the value of a dimension if it's set.
func (m *Metric) GetDimensionValue(dimension string, defaults map[string]string) (value string, ok bool) {
	dimension = sanitizeString(dimension)
	for name, value := range m.GetDimensions(defaults) {
		if name == dimension {
			return value, true
		}
	}
	return "", false
}

func sanitizeString(s string) string {
	s = strings.Replace(s, "=", "-", -1)
	s = strings.Replace(s, ":", "-", -1)
	return s
}
