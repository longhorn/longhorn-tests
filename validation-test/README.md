# Validation tests for Rancher

### Pre-reqs

A running Rancher Environment, with `rancher-longhorn` driver available.


### Running

Export `CATTLE_TEST_URL`, `CATTLE_ACCESS_KEY`, `CATTLE_SECRET_KEY` environment variables

```bash
export CATTLE_TEST_URL='http://1.2.3.4:8080'
export CATTLE_ACCESS_KEY='ABCDEF1234567890'
export CATTLE_SECRET_KEY='ABCDEF1234567890ABCDEF1234567890'
```

Clone this repo:

```bash
git https://github.com/rancher/longhorn-tests.git
```

To run:

```bash
cd validation-tests
tox
```

### Running in a container

You can use [dapper](https://github.com/rancher/dapper) to run the tests in a container. To drop into the container, run:

```bash
dapper -s
```

In the container shell run:

```bash
cd validation-tests
tox
```


## Contact
For bugs, questions, comments, corrections, suggestions, etc., open an issue in
 [rancher/rancher](//github.com/rancherlabs/converged-infra/issues) with a title starting with `[Validation-Tests] `.

Or just [click here](//github.com/rancherlabs/converged-infra/issues/new?title=%5BValidation-Tests%5D%20) to create a new issue.

you may not use this file except in compliance with the License.
You may obtain a copy of the License at

[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

