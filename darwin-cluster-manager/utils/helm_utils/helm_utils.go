package helm_utils

import (
	"compute/cluster_manager/constants"
	"compute/cluster_manager/utils/logger"
	"compute/cluster_manager/utils/rest_errors"
	"context"
	"fmt"
	"go.uber.org/zap"
	"helm.sh/helm/v3/pkg/chart"
	"helm.sh/helm/v3/pkg/chartutil"
	"os"
	"strings"
	"time"

	"helm.sh/helm/v3/pkg/action"
	"helm.sh/helm/v3/pkg/chart/loader"
	"helm.sh/helm/v3/pkg/kube"
	"helm.sh/helm/v3/pkg/release"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
)

// PackHelm TODO get the chart from s3 or other source
func PackHelm(chartPath string, valsPath string, destinationPath string) (string, rest_errors.RestErr) {
	input, err := os.ReadFile(valsPath)
	if err != nil {
		restError := rest_errors.NewInternalServerError("Failed to read values.yaml file", err)
		return "", restError
	}
	destinationFile := chartPath + "/values.yaml"
	err = os.WriteFile(destinationFile, input, 0644)
	if err != nil {
		restError := rest_errors.NewInternalServerError("failed to write to destination file", err)
		return "", restError
	}
	packageClient := action.NewPackage()
	packageClient.Destination = destinationPath
	p, err := packageClient.Run(chartPath, make(map[string]interface{}))
	if err != nil {
		restError := rest_errors.NewInternalServerError("Failed to package the helm chart", err)
		return "", restError
	}
	return p, nil
}

func PackHelmV2(requestId string, chartPath string, valsPath string, destinationPath string) (string, rest_errors.RestErr) {
	values, err := chartutil.ReadValuesFile(valsPath)
	if err != nil {
		logger.ErrorR(requestId, "Failed to read values.yaml file", zap.Any("Error", err))
		return "", rest_errors.NewInternalServerError("Failed to read values.yaml file", err)
	}

	// Package chart with the given values
	path, err := PackageWithValues(chartPath, values, destinationPath)
	if err != nil {
		logger.ErrorR(requestId, "Failed to package the helm chart", zap.Any("Error", err))
		return "", rest_errors.NewInternalServerError("Failed to package the helm chart", err)
	}

	return path, nil
}

// UnpackHelm extracts a Helm chart tarball (.tgz) into the specified destination directory.
func UnpackHelm(requestId string, packedChartPath string) (*chart.Chart, rest_errors.RestErr) {
	// Open the Packaged Helm Chart
	file, err := os.Open(packedChartPath)
	if err != nil {
		logger.ErrorR(requestId, "Failed to open the packaged helm chart", zap.Any("Error", err))
		return nil, rest_errors.NewInternalServerError("Failed to open the packaged helm chart", err)
	}
	defer file.Close()

	// Unpack the Helm Chart
	chartPath, err := loader.LoadArchive(file)
	if err != nil {
		logger.ErrorR(requestId, "Failed to load the packaged helm chart", zap.Any("Error", err))
		return nil, rest_errors.NewInternalServerError("Failed to load the packaged helm chart", err)
	}

	logger.DebugR(requestId, "Successfully unpacked the helm chart", zap.Any("chartPath", chartPath))
	return chartPath, nil
}

func InstallorUpgradeHelmChart(kubeConfigPath string, chartPath string, releaseName string, namespace string) (*release.Release, rest_errors.RestErr) {
	chart, err := loader.Load(chartPath)
	if err != nil {
		logger.Error("Error loading the chart", zap.Error(err))
		restError := rest_errors.NewInternalServerError("Error loading the chart", err)
		return nil, restError
	}
	releaseNamespace := namespace
	actionConfig := new(action.Configuration)
	if err := actionConfig.Init(kube.GetConfig(kubeConfigPath, "", releaseNamespace), releaseNamespace, os.Getenv("HELM_DRIVER"), func(format string, v ...interface{}) {
		_ = fmt.Sprintf(format, v)
	}); err != nil {
		logger.Error("Error initiating the action config", zap.Error(err))
		restError := rest_errors.NewInternalServerError("Error initiating the action config", err)
		return nil, restError
	}

	statusCli := action.NewStatus(actionConfig)
	releaseResp, err := statusCli.Run(releaseName)
	if err != nil && err.Error() == "release: not found" {
		installClient := action.NewInstall(actionConfig)
		installClient.Namespace = releaseNamespace
		installClient.ReleaseName = releaseName
		installClient.CreateNamespace = true
		rel, err := installClient.Run(chart, nil)
		if err != nil && err.Error() == "release: already exists" {
			fmt.Println(fmt.Sprintf("Concurrent Request with %s, duplicate call", releaseName))
		} else if err != nil {
			logger.Error("Error installing helm release", zap.Error(err))
			restError := rest_errors.NewInternalServerError("Error installing helm release", err)
			return nil, restError
		}
		return rel, nil
	} else if err != nil {
		logger.Error("Error getting the status of helm release", zap.Error(err))
		restError := rest_errors.NewInternalServerError("Error getting the status of helm release", err)
		return nil, restError
	} else if releaseResp.Info.Status == "deployed" {
		upgradeClient := action.NewUpgrade(actionConfig)
		upgradeClient.Namespace = releaseNamespace
		rel, err := upgradeClient.Run(releaseName, chart, nil)
		if err != nil {
			if err.Error() == "release: already exists" {
				fmt.Println("not an error, duplicate call")
			} else {
				restError := rest_errors.NewInternalServerError("Error upgrading helm release", err)
				return nil, restError
			}
		}
		return rel, nil
	} else {
		logger.Error("Failed to InstallorUpgrade as the release state is", zap.String("status", releaseResp.Info.Status.String()))
		errMsg := "Failed to InstallorUpgrade as the release state is" + releaseResp.Info.Status.String()
		restError := rest_errors.NewInternalServerError(errMsg, err)
		return nil, restError
	}
}

func InstallorUpgradeHelmChartWithRetries(kubeConfigPath string, chartPath string, releaseName string, namespace string) (*release.Release, rest_errors.RestErr) {
	retries := 0
	var err rest_errors.RestErr
	for retries < 3 {
		logger.Info("Attempting to install or upgrade Helm chart",
			zap.Int("attempt", retries+1),
			zap.String("release", releaseName),
			zap.String("namespace", namespace),
			zap.String("chartPath", chartPath),
		)
		_, err = InstallorUpgradeHelmChart(kubeConfigPath, chartPath, releaseName, namespace)
		if err == nil {
			cleanupErr := CleanupOldHelmSecrets(releaseName, namespace, kubeConfigPath, constants.MaxSecretHistory)
			if cleanupErr != nil {
				logger.ErrorR("Failed to cleanup old helm releases %s", cleanupErr.Error())
			}
			return nil, nil
		}
		// TODO - to load test on high number of clusters, services and remove the time.sleep
		time.Sleep(1 * time.Second) // Wait before deleting the release and retrying
		logger.Info("Deleting old Helm release to retry installation again that failed due to error", zap.String("release", releaseName), zap.String("namespace", namespace), zap.Error(err))
		_, err := DeleteHelmRelease(kubeConfigPath, releaseName, namespace)
		if err != nil {
			logger.Error("Failed to delete old Helm release", zap.String("release", releaseName), zap.String("namespace", namespace), zap.Error(err))
			// If we can't delete the old release, we might not be able to proceed
			return nil, rest_errors.NewInternalServerError("Failed to delete old Helm release", err)
		}
		logger.Info("Deleted old Helm release %s, retrying installation", zap.String("release", releaseName), zap.String("namespace", namespace))
		logger.Error("Error installing or upgrading Helm chart",
			zap.Int("attempt", retries+1),
			zap.String("release", releaseName),
			zap.String("namespace", namespace),
			zap.String("chartPath", chartPath),
			zap.Error(err),
		)
		retries += 1
		time.Sleep(2 * time.Second) // Wait before retrying
	}

	return nil, err
}

func DeleteHelmRelease(kubeConfigPath string, releaseName string, namespace string) (bool, rest_errors.RestErr) {
	releaseNamespace := namespace
	actionConfig := new(action.Configuration)
	if err := actionConfig.Init(kube.GetConfig(kubeConfigPath, "", releaseNamespace), releaseNamespace, os.Getenv("HELM_DRIVER"), func(format string, v ...interface{}) {
		_ = fmt.Sprintf(format, v)
	}); err != nil {
		restError := rest_errors.NewInternalServerError("Error initiating the action config in delete helm release", err)
		return false, restError
	}
	deleteClient := action.NewUninstall(actionConfig)
	_, err := deleteClient.Run(releaseName)
	if err != nil && !strings.Contains(err.Error(), "release: not found") {
		restError := rest_errors.NewInternalServerError("Error uninstalling the helm release", err)
		return false, restError
	}
	return true, nil
}

func RestartHelmRelease(kubeConfigPath string, chartPath string, releaseName string, namespace string) (*release.Release, rest_errors.RestErr) {
	_, err := DeleteHelmRelease(kubeConfigPath, releaseName, namespace)
	if err != nil {
		return nil, err
	}
	time.Sleep(5 * time.Second)
	rel, err := InstallorUpgradeHelmChartWithRetries(kubeConfigPath, chartPath, releaseName, namespace)
	if err != nil {
		return nil, err
	}
	return rel, nil
}

func GetUrl(kubeConfigPath string, name string, namespace string) (string, rest_errors.RestErr) {

	config, err := clientcmd.BuildConfigFromFlags("", kubeConfigPath)
	if err != nil {
		restError := rest_errors.NewInternalServerError("Error building kube config", err)
		return "", restError
	}
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		restError := rest_errors.NewInternalServerError("Error creating kube client", err)
		return "", restError
	}
	k8sClient := clientset.NetworkingV1()
	getOptions := metav1.GetOptions{}
	ing, err := k8sClient.Ingresses(namespace).Get(context.TODO(), name, getOptions)

	if err != nil {
		restError := rest_errors.NewInternalServerError("Error getting service", err)
		return "", restError
	}
	fmt.Println(ing.Status.LoadBalancer.Ingress)
	return ing.Status.LoadBalancer.Ingress[0].Hostname, nil
}
