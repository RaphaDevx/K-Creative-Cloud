//! Project-local document graph. Native files are never opened or removed here.
use crate::{id, Result};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};

const MAX_DOCUMENTS: usize = 4096;
const MAX_LINKS: usize = 16384;
const MAX_MANIFEST_BYTES: usize = 262144;

#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Document {
    id: String,
    name: String,
    kind: String,
    content: Value,
    #[serde(default)]
    archived: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    owner_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    origin_id: Option<String>,
}

#[derive(Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct Link {
    dependent_id: String,
    source_id: String,
}

#[derive(Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Graph {
    documents: Vec<Document>,
    links: Vec<Link>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    last_archive: Option<Value>,
}

fn load(project: &Value) -> Result<Graph> {
    match project.get("document_graph") {
        Some(value) => serde_json::from_value(value.clone()).map_err(|e| e.to_string()),
        None => Ok(Graph::default()),
    }
}

fn string<'a>(params: &'a Value, key: &str) -> Result<&'a str> {
    params[key].as_str().ok_or_else(|| format!("Missing {key}"))
}

impl Graph {
    fn active(&self, doc_id: &str) -> Result<&Document> {
        self.documents
            .iter()
            .find(|doc| doc.id == doc_id && !doc.archived)
            .ok_or_else(|| format!("Active document not found: {doc_id}"))
    }

    // Iterative traversal avoids recursion depth failures in long dependency chains.
    fn reachable(&self, root: &str, dependents: bool) -> BTreeSet<String> {
        let active: BTreeSet<&str> = self
            .documents
            .iter()
            .filter(|doc| !doc.archived)
            .map(|doc| doc.id.as_str())
            .collect();
        let mut adjacency: BTreeMap<&str, Vec<&str>> = BTreeMap::new();
        for link in &self.links {
            if active.contains(link.dependent_id.as_str())
                && active.contains(link.source_id.as_str())
            {
                let (from, to) = if dependents {
                    (link.source_id.as_str(), link.dependent_id.as_str())
                } else {
                    (link.dependent_id.as_str(), link.source_id.as_str())
                };
                adjacency.entry(from).or_default().push(to);
            }
        }
        let mut seen = BTreeSet::new();
        let mut stack = vec![root];
        while let Some(current) = stack.pop() {
            if seen.insert(current.to_string()) {
                if let Some(next) = adjacency.get(current) {
                    stack.extend(next.iter().copied());
                }
            }
        }
        seen
    }

    fn direct_dependents(&self, source: &str) -> BTreeSet<String> {
        self.links
            .iter()
            .filter(|link| link.source_id == source && self.active(&link.dependent_id).is_ok())
            .map(|link| link.dependent_id.clone())
            .collect()
    }

    fn preview(&self, project: &Value, params: &Value) -> Result<Value> {
        let target = string(params, "id")?;
        self.active(target)?;
        let mode = string(params, "mode")?;
        let direct = self.direct_dependents(target);
        let affected = match mode {
            "preserve_dependents" => BTreeSet::from([target.to_string()]),
            "cascade_dependents" => self.reachable(target, true),
            _ => return Err("Invalid archive mode".into()),
        };
        let documents: Vec<_> = affected
            .iter()
            .map(|doc_id| {
                let doc = self.active(doc_id).unwrap();
                json!({"id":doc.id,"name":doc.name,"kind":doc.kind})
            })
            .collect();
        Ok(json!({
            "expected_revision": project["revision"], "id": target, "mode": mode,
            "archive": documents,
            "preserve_for": if mode == "preserve_dependents" { direct } else { BTreeSet::new() },
            "physical_files_deleted": false,
            "scope": "project_manifest_only"
        }))
    }
}

pub fn preview(project: &Value, params: &Value) -> Result<Value> {
    load(project)?.preview(project, params)
}

pub fn apply(project: &mut Value, action: &str, params: &Value) -> Result<()> {
    let mut graph = load(project)?;
    match action {
        "document.create" => {
            if graph.documents.len() >= MAX_DOCUMENTS {
                return Err("Document limit reached".into());
            }
            let content = &params["content"];
            if !content.is_object()
                || serde_json::to_vec(content)
                    .map_err(|e| e.to_string())?
                    .len()
                    > MAX_MANIFEST_BYTES
            {
                return Err("Document content must be an object of at most 256 KiB".into());
            }
            graph.documents.push(Document {
                id: id(),
                name: string(params, "name")?.into(),
                kind: string(params, "kind")?.into(),
                content: content.clone(),
                archived: false,
                owner_id: None,
                origin_id: None,
            });
        }
        "document.link" => {
            let dependent = string(params, "dependent_id")?;
            let source = string(params, "source_id")?;
            graph.active(dependent)?;
            graph.active(source)?;
            let link = Link {
                dependent_id: dependent.into(),
                source_id: source.into(),
            };
            if graph.links.contains(&link) {
                return Err("Document link already exists".into());
            }
            if graph.links.len() >= MAX_LINKS {
                return Err("Document link limit reached".into());
            }
            if graph.reachable(source, false).contains(dependent) {
                return Err("Document dependency would create a cycle".into());
            }
            graph.links.push(link);
        }
        "document.archive" => {
            if params["expected_revision"].as_u64() != project["revision"].as_u64() {
                return Err("Project changed; request a new archive preview".into());
            }
            let report = graph.preview(project, params)?;
            let target = string(params, "id")?;
            let mut replacements = Vec::new();
            if params["mode"] == "preserve_dependents" {
                let original = graph.active(target)?.clone();
                let upstream: Vec<_> = graph
                    .links
                    .iter()
                    .filter(|link| link.dependent_id == target)
                    .cloned()
                    .collect();
                let dependents = graph.direct_dependents(target);
                if graph.documents.len() + dependents.len() > MAX_DOCUMENTS
                    || graph.links.len() + upstream.len() * dependents.len() > MAX_LINKS
                {
                    return Err("Preserved copies exceed document graph limits".into());
                }
                for dependent in dependents {
                    let mut snapshot = original.clone();
                    snapshot.id = id();
                    snapshot.owner_id = Some(dependent.clone());
                    snapshot.origin_id = Some(target.into());
                    for link in &mut graph.links {
                        if link.dependent_id == dependent && link.source_id == target {
                            link.source_id = snapshot.id.clone();
                        }
                    }
                    for link in &upstream {
                        graph.links.push(Link {
                            dependent_id: snapshot.id.clone(),
                            source_id: link.source_id.clone(),
                        });
                    }
                    replacements.push(json!({"dependent_id":dependent,"original_id":target,"copy_id":snapshot.id}));
                    graph.documents.push(snapshot);
                }
            }
            let archived: BTreeSet<_> = report["archive"]
                .as_array()
                .unwrap()
                .iter()
                .map(|doc| doc["id"].as_str().unwrap().to_string())
                .collect();
            for doc in &mut graph.documents {
                if archived.contains(&doc.id) {
                    doc.archived = true;
                }
            }
            graph.last_archive = Some(json!({"preview":report,"replacements":replacements}));
        }
        _ => return Err("Unknown document action".into()),
    }
    // Publish only after the complete graph operation succeeds.
    project["document_graph"] = serde_json::to_value(graph).map_err(|e| e.to_string())?;
    Ok(())
}
