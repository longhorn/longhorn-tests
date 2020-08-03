<?xml version="1.0" ?>
<testsuites>
{{- range . -}}
{{- $failures := len .Vulnerabilities }}
    <testsuite tests="1" failures="{{ $failures }}" time="" name="{{  .Target }}">
    {{- if not (eq .Type "") }}
        <properties>
            <property name="type" value="{{ .Type }}"></property>
        </properties>
        {{- end -}}
        {{ range .Vulnerabilities }}
        <testcase classname="LONGHORN_IMAGE_NAME.{{ .VulnerabilityID }}" name="{{ .PkgName }}-{{ .InstalledVersion }} [{{ .Vulnerability.Severity }}]" time="">
            <failure message={{escapeXML .Title | printf "%q" }} type="description">{{escapeXML .Description | printf "%q" }}</failure>
        </testcase>
    {{- end }}
    </testsuite>
{{- end }}
</testsuites>
